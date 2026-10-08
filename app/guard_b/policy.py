import re
import time
from typing import Any
from app.config import load_profile
from app.models import RequestContext, StageResult
from app.sessions import get_session

CANARY_REGEX = re.compile(r"CANARY_[0-9a-f]{12}")


def evaluate_tool_call(
    ctx: RequestContext, tool_name: str, args: dict[str, Any]
) -> tuple[str, str]:
    # 1. Allow-list check
    if tool_name not in ctx.offered_tools:
        return "BLOCKED", f"Tool '{tool_name}' was not offered to the model"

    profile_data = load_profile(ctx.profile)
    tools_cfg = profile_data.get("tools", {})
    tool_cfg = tools_cfg.get(tool_name, {})
    is_risky = tool_cfg.get("risky", False)

    # 2. Canary check in args (exact match or regex CANARY_[0-9a-f]{12})
    args_str = str(args)
    if ctx.canary and ctx.canary in args_str:
        return "BLOCKED", "System prompt canary leaked in tool arguments (LLM07)"
    if CANARY_REGEX.search(args_str):
        return "BLOCKED", "Canary pattern detected in tool arguments (LLM07)"

    # 3. Hard rules (profile specific)
    if tool_name == "lookup_record":
        rec_id = str(args.get("record_id", "")).strip()
        pattern = tool_cfg.get("record_id_pattern")
        if not rec_id or rec_id.lower() in ("all", "*") or "," in rec_id:
            return (
                "BLOCKED",
                "Multiple/wildcard record access not allowed (LLM06)",
            )
        if pattern and not re.match(pattern, rec_id):
            return (
                "BLOCKED",
                f"Record ID '{rec_id}' does not match pattern {pattern}",
            )

    elif tool_name == "read_document":
        doc_name = str(args.get("name", "")).strip()
        if ".." in doc_name or doc_name.startswith("/") or "\\" in doc_name:
            return "BLOCKED", "Path traversal in document name blocked"

    elif tool_name == "send_email":
        to_addr = str(args.get("to", "")).strip()
        allowed_domains = tool_cfg.get("allowed_email_domains", [])
        domain = to_addr.split("@")[-1] if "@" in to_addr else ""
        if domain not in allowed_domains:
            return (
                "BLOCKED",
                f"Recipient domain '{domain}' not in allowed list {allowed_domains}",
            )

    # Hard rules passed. If policy layer off -> allow
    if not ctx.layers.policy_engine:
        return "ALLOWED", "Policy layer off (demo mode)"

    session = get_session(ctx.session_id)

    # 4. Taint rule
    if is_risky and session.taint:
        on_taint = profile_data.get("on_taint", "block")
        if on_taint == "block":
            return "BLOCKED", "Risky tool blocked because session is tainted"
        elif on_taint == "approve":
            return (
                "NEEDS_APPROVAL",
                "Risky tool requires user approval because session is tainted",
            )

    # 5. Goal-consistency check
    user_msgs = [
        s.text.lower()
        for s in ctx.segments
        if s.trust == "trusted" and s.source == "user"
    ]
    latest_user_text = " ".join(user_msgs)
    intents = profile_data.get("intents", {}).get(tool_name, [])

    matches_intent = any(keyword in latest_user_text for keyword in intents)
    if not matches_intent:
        if is_risky:
            return (
                "NEEDS_APPROVAL",
                f"Risky tool '{tool_name}' goal-consistency check failed",
            )

    return "ALLOWED", "Policy checks passed"


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    try:
        if not ctx.tool_calls:
            ms = (time.perf_counter() - start_t) * 1000.0
            return StageResult(
                step=8,
                name="policy",
                guard="B",
                status="INFO",
                reason="No tool calls",
                ms=ms,
            )

        has_blocked = any(tc.status == "BLOCKED" for tc in ctx.tool_calls)
        has_pending = any(
            tc.status == "PENDING_APPROVAL" for tc in ctx.tool_calls
        )

        if has_blocked:
            status = "BLOCKED"
            reason_str = "One or more tool calls were blocked by policy"
        elif has_pending:
            status = "FLAGGED"
            reason_str = "Tool call pending user approval"
        else:
            status = "PASSED"
            reason_str = f"All {len(ctx.tool_calls)} tool calls approved by policy"

        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=8,
            name="policy",
            guard="B",
            status=status,
            reason=reason_str,
            ms=ms,
        )
    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=8,
            name="policy",
            guard="B",
            status="ERROR",
            reason=f"Error in policy engine: {e}",
            ms=ms,
        )
