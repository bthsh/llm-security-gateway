import uuid
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Form, File, UploadFile, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.assistant import loop as assistant_loop, tools as tool_impl
from app.audit.log import init_db, get_recent_requests
from app.config import list_profiles, settings
from app.models import (
    RequestContext,
    Segment,
    ChatResponse,
    LayerSettings,
    ToolCall,
)
from app.pipeline import run_pipeline, run_guard_a
from app.sessions import get_session, reset_session, update_layers


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="LLM Security Gateway", lifespan=lifespan)


@app.get("/api/health")
def get_health():
    return {
        "status": "ok",
        "gateway": "online",
        "backend": settings.LLM_BACKEND,
        "gemini_model": settings.GEMINI_MODEL,
        "classifier": settings.CLASSIFIER_MODEL,
    }


@app.get("/api/profiles")
def get_profiles():
    return list_profiles()


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

    if files:
        for f in files:
            content = await f.read()
            text_content = content.decode("utf-8", errors="ignore")
            segments.append(
                Segment(
                    id=f"seg_{uuid.uuid4().hex[:8]}",
                    source="document",
                    trust="untrusted",
                    text=text_content,
                    origin=f.filename,
                )
            )

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
        outbox=ctx.outbox,
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

    if files:
        for f in files:
            content = await f.read()
            text_content = content.decode("utf-8", errors="ignore")
            segments.append(
                Segment(
                    id=f"seg_{uuid.uuid4().hex[:8]}",
                    source="document",
                    trust="untrusted",
                    text=text_content,
                    origin=f.filename,
                )
            )

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
        ctx = run_pipeline(ctx, is_scan_mode=False)
    else:
        ctx = run_pipeline(ctx, is_scan_mode=False)

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
        # User approved -> run tool
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


@app.get("/api/logs")
def get_logs(limit: int = Query(50)):
    return get_recent_requests(limit)
