import json
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.assistant import loop as assistant_loop, tools as tool_impl
from app.audit.log import init_db, get_recent_requests, get_latest_metrics
from app.config import list_profiles, settings, BASE_DIR
from app.models import (
    RequestContext,
    Segment,
    ChatResponse,
    LayerSettings,
    ToolCall,
)
from app.pipeline import run_pipeline, run_guard_a, run_guard_b
from app.sessions import get_session, reset_session, update_layers
from app.guard_a.classifier import classifier
from app.guard_b import policy


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    classifier.warmup()
    yield


app = FastAPI(title="LLM Security Gateway", lifespan=lifespan)


@app.get("/api/health")
def get_health():
    active_model = (
        settings.GROQ_MODEL
        if settings.LLM_BACKEND == "groq"
        else (
            settings.OLLAMA_MODEL
            if settings.LLM_BACKEND == "ollama"
            else settings.GEMINI_MODEL
        )
    )
    return {
        "status": "ok",
        "gateway": "online",
        "backend": settings.LLM_BACKEND,
        "model": active_model,
        "gemini_model": settings.GEMINI_MODEL,
        "groq_model": settings.GROQ_MODEL,
        "classifier": settings.CLASSIFIER_MODEL,
    }


@app.get("/api/profiles")
def get_profiles():
    return list_profiles()


@app.get("/api/samples")
def list_samples():
    samples_dir = BASE_DIR / "data" / "samples"
    results = []
    if samples_dir.exists():
        for p in sorted(samples_dir.glob("*")):
            if p.is_file():
                ext = p.suffix.lower()
                type_name = ext.replace(".", "").upper()
                name_title = p.stem.replace("_", " ").title()
                results.append(
                    {
                        "id": p.name,
                        "name": name_title,
                        "filename": p.name,
                        "type": type_name,
                    }
                )
    return results


@app.get("/api/samples/{name}")
def get_sample_content(name: str):
    sample_path = BASE_DIR / "data" / "samples" / name
    if not sample_path.exists() or not sample_path.is_file():
        raise HTTPException(status_code=404, detail="Sample file not found")
    content = sample_path.read_text(encoding="utf-8", errors="ignore")
    return {"id": name, "filename": name, "content": content}


def build_segments(
    message: Optional[str],
    files: Optional[list[UploadFile]],
    sample: Optional[str],
) -> list[Segment]:
    segments = []
    if message and message.strip():
        segments.append(
            Segment(
                id=f"seg_{uuid.uuid4().hex[:8]}",
                source="user",
                trust="trusted",
                text=message,
                origin="user_message",
            )
        )

    if sample:
        sample_path = BASE_DIR / "data" / "samples" / sample
        if sample_path.exists() and sample_path.is_file():
            raw_bytes = sample_path.read_bytes()
            ext = sample_path.suffix.lower()
            source = "email" if ext == ".eml" else "document"
            text_val = (
                raw_bytes.decode("utf-8", errors="ignore")
                if ext != ".pdf"
                else raw_bytes.decode("latin-1")
            )
            segments.append(
                Segment(
                    id=f"seg_{uuid.uuid4().hex[:8]}",
                    source=source,
                    trust="untrusted",
                    text=text_val,
                    origin=sample,
                )
            )

    if files:
        for f in files:
            raw_bytes = f.file.read()
            ext = Path(f.filename).suffix.lower()
            source = "email" if ext == ".eml" else "document"
            text_val = (
                raw_bytes.decode("utf-8", errors="ignore")
                if ext != ".pdf"
                else raw_bytes.decode("latin-1")
            )
            segments.append(
                Segment(
                    id=f"seg_{uuid.uuid4().hex[:8]}",
                    source=source,
                    trust="untrusted",
                    text=text_val,
                    origin=f.filename,
                )
            )

    return segments


@app.post("/api/scan", response_model=ChatResponse)
async def scan_endpoint(
    session_id: str = Form(...),
    profile: str = Form("customer_support"),
    message: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),
    sample: Optional[str] = Form(None),
):
    req_id = f"req_{uuid.uuid4().hex[:12]}"
    session = get_session(session_id)
    segments = build_segments(message, files, sample)

    ctx = RequestContext(
        request_id=req_id,
        session_id=session_id,
        profile=profile,
        layers=session.layers,
        segments=segments,
    )

    ctx = run_pipeline(ctx, is_scan_mode=True)

    return ChatResponse(
        request_id=ctx.request_id,
        session_id=ctx.session_id,
        profile=ctx.profile,
        decision=ctx.decision,
        decision_reason=ctx.decision_reason,
        reply=ctx.reply or "",
        trace=ctx.trace,
        before_after=ctx.before_after,
        hidden_tools=ctx.hidden_tools,
        tool_calls=ctx.tool_calls,
        pending_action=ctx.pending_action,
        outbox=session.outbox,
        redactions=ctx.redactions,
        timings=ctx.timings,
        layers=ctx.layers,
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(
    session_id: str = Form(...),
    profile: str = Form("customer_support"),
    message: Optional[str] = Form(None),
    files: Optional[list[UploadFile]] = File(None),
    sample: Optional[str] = Form(None),
):
    req_id = f"req_{uuid.uuid4().hex[:12]}"
    session = get_session(session_id)
    segments = build_segments(message, files, sample)

    ctx = RequestContext(
        request_id=req_id,
        session_id=session_id,
        profile=profile,
        layers=session.layers,
        segments=segments,
    )

    # Run full pipeline with assistant loop
    ctx = run_guard_a(ctx)
    if ctx.decision != "BLOCKED":
        ctx = assistant_loop.run_assistant_loop(ctx)
        # Final pipeline completion & Guard B
        ctx = run_guard_b(ctx)

    # Ensure BLOCKED_ACTION final decision if any tool call was blocked at Step 8
    blocked_calls = [tc for tc in ctx.tool_calls if tc.status == "BLOCKED"]
    if blocked_calls and ctx.decision in ("ALLOWED", "CLEANED"):
        ctx.decision = "BLOCKED_ACTION"
        ctx.decision_reason = blocked_calls[0].reason

    return ChatResponse(
        request_id=ctx.request_id,
        session_id=ctx.session_id,
        profile=ctx.profile,
        decision=ctx.decision,
        decision_reason=ctx.decision_reason,
        reply=ctx.reply or "",
        trace=ctx.trace,
        before_after=ctx.before_after,
        hidden_tools=ctx.hidden_tools,
        tool_calls=ctx.tool_calls,
        pending_action=ctx.pending_action,
        outbox=session.outbox,
        redactions=ctx.redactions,
        timings=ctx.timings,
        layers=ctx.layers,
    )


@app.post("/api/approve", response_model=ChatResponse)
async def approve_endpoint(
    session_id: str = Form(...),
    pending_id: str = Form(...),
    approve: bool = Form(...),
):
    session = get_session(session_id)
    pending = session.pending_action

    if not pending or pending.id != pending_id:
        raise HTTPException(
            status_code=400, detail="Invalid or expired pending approval request"
        )

    req_id = f"req_{uuid.uuid4().hex[:12]}"
    ctx = RequestContext(
        request_id=req_id,
        session_id=session_id,
        profile="customer_support",
        layers=session.layers,
    )

    if approve:
        # Re-evaluate policy hard rules before executing tool (Decision D-22)
        ctx.offered_tools = [pending.tool]
        status, pol_reason = policy.evaluate_tool_call(ctx, pending.tool, pending.args)

        if status == "BLOCKED":
            ctx.tool_calls.append(
                ToolCall(
                    tool=pending.tool,
                    args=pending.args,
                    status="BLOCKED",
                    reason=f"Approved by user, but blocked by hard policy rule: {pol_reason}",
                )
            )
            ctx.reply = f"Action '{pending.tool}' was approved, but stopped by hard security rule: {pol_reason}"
            ctx.decision = "BLOCKED"
            ctx.decision_reason = f"Hard policy rule blocked action: {pol_reason}"
        else:
            tool_output = ""
            if pending.tool == "send_email":
                to_addr = pending.args.get("to", "")
                subj = pending.args.get("subject", "")
                body = pending.args.get("body", "")
                tool_output = tool_impl.execute_send_email(
                    session_id, to_addr, subj, body
                )
            ctx.tool_calls.append(
                ToolCall(
                    tool=pending.tool,
                    args=pending.args,
                    status="APPROVED",
                    reason="Approved by user",
                )
            )
            ctx.reply = f"Action '{pending.tool}' approved and executed. {tool_output}"
            ctx.decision = "ALLOWED"
            ctx.decision_reason = "Approved by user"
    else:
        ctx.tool_calls.append(
            ToolCall(
                tool=pending.tool,
                args=pending.args,
                status="DENIED",
                reason="Denied by user",
            )
        )
        ctx.reply = f"Action '{pending.tool}' denied by user."
        ctx.decision = "BLOCKED_ACTION"
        ctx.decision_reason = "Denied by user"

    session.pending_action = None

    return ChatResponse(
        request_id=ctx.request_id,
        session_id=ctx.session_id,
        profile=ctx.profile,
        decision=ctx.decision,
        decision_reason=ctx.decision_reason,
        reply=ctx.reply,
        trace=ctx.trace,
        before_after=ctx.before_after,
        hidden_tools=ctx.hidden_tools,
        tool_calls=ctx.tool_calls,
        pending_action=None,
        outbox=session.outbox,
        redactions=ctx.redactions,
        timings=ctx.timings,
        layers=ctx.layers,
    )


@app.get("/api/layers")
def get_session_layers(session_id: str = Query(...)):
    session = get_session(session_id)
    return session.layers


@app.post("/api/layers")
def post_session_layers(
    session_id: str = Form(...), layer: str = Form(...), value: bool = Form(...)
):
    try:
        updated = update_layers(session_id, {layer: value})
        return updated
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/reset")
def post_reset_session(session_id: str = Form(...)):
    session = reset_session(session_id)
    return {"session_id": session.session_id, "status": "reset"}


@app.get("/api/outbox")
def get_session_outbox(session_id: str = Query(...)):
    session = get_session(session_id)
    return session.outbox


@app.get("/api/logs")
def get_logs(limit: int = Query(50)):
    return get_recent_requests(limit)


@app.get("/api/metrics")
def get_metrics():
    return get_latest_metrics()


@app.post("/api/testset")
def save_to_testset(
    request_id: str = Form(None),
    session_id: str = Form(None),
    profile: str = Form("customer_support"),
    message: Optional[str] = Form(None),
    sample: Optional[str] = Form(None),
):
    test_dir = BASE_DIR / "tests" / "data"
    test_dir.mkdir(parents=True, exist_ok=True)
    file_path = test_dir / "user_saved_testset.json"

    item = {
        "id": request_id or f"test_{uuid.uuid4().hex[:8]}",
        "profile": profile,
        "message": message or "",
        "sample": sample or "",
        "saved_at": datetime.now(timezone.utc).isoformat(),
    }

    existing = []
    if file_path.exists():
        try:
            existing = json.loads(file_path.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    existing.append(item)
    file_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")
    return {"status": "saved", "id": item["id"]}


@app.post("/v1/chat/completions")
async def chat_completions(req: dict):
    messages = req.get("messages", [])
    model = req.get("model", settings.GEMINI_MODEL)

    user_text = ""
    for m in messages:
        if m.get("role") == "user":
            user_text = m.get("content", "")

    req_id = f"req_{uuid.uuid4().hex[:12]}"
    session_id = f"sess_openai_{uuid.uuid4().hex[:8]}"
    ctx = RequestContext(
        request_id=req_id,
        session_id=session_id,
        profile="customer_support",
        segments=[Segment(id="seg_1", source="user", trust="trusted", text=user_text)],
    )
    ctx = run_guard_a(ctx)
    if ctx.decision != "BLOCKED":
        ctx = assistant_loop.run_assistant_loop(ctx)
        ctx = run_pipeline(ctx, is_scan_mode=False)
    else:
        ctx = run_pipeline(ctx, is_scan_mode=False)

    finish_reason = "stop"
    reply_content = ctx.reply or ""
    if ctx.decision == "BLOCKED":
        finish_reason = "content_filter"
        reply_content = f"Request blocked: {ctx.decision_reason}"

    return {
        "id": f"chatcmpl-{req_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": reply_content},
                "finish_reason": finish_reason,
            }
        ],
        "gateway": {
            "request_id": ctx.request_id,
            "decision": ctx.decision,
            "reason": ctx.decision_reason,
        },
    }


# Mount UI static files at root
ui_dir = BASE_DIR / "ui"
if ui_dir.exists():
    app.mount("/", StaticFiles(directory=str(ui_dir), html=True), name="ui")
