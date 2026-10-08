import secrets
import time
from app.config import load_profile
from app.models import RequestContext, StageResult
from app.sessions import get_session


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    try:
        ctx.canary = f"CANARY_{secrets.token_hex(6)}"
        session = get_session(ctx.session_id)

        profile_data = load_profile(ctx.profile)
        tools_dict = profile_data.get("tools", {})

        offered = []
        hidden = []

        for tool_name, tool_cfg in tools_dict.items():
            is_risky = tool_cfg.get("risky", False)
            if session.taint and is_risky and ctx.layers.tool_scoping:
                hidden.append(tool_name)
            else:
                offered.append(tool_name)

        ctx.offered_tools = offered
        ctx.hidden_tools = hidden

        ms = (time.perf_counter() - start_t) * 1000.0
        reason_msg = f"Canary planted ({ctx.canary[:12]}...); offered={offered}"
        if hidden:
            reason_msg += f", hidden={hidden} (session tainted)"

        return StageResult(
            step=7,
            name="canary_tools",
            guard="A",
            status="INFO",
            reason=reason_msg,
            ms=ms,
        )
    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=7,
            name="canary_tools",
            guard="A",
            status="ERROR",
            reason=f"Error in canary_tools: {e}",
            ms=ms,
        )
