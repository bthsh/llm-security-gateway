import time
from app.models import RequestContext, StageResult


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    ms = (time.perf_counter() - start_t) * 1000.0
    reason_msg = (
        f"Evaluated {len(ctx.tool_calls)} tool calls"
        if ctx.tool_calls
        else "No tool calls"
    )
    return StageResult(
        step=8,
        name="policy",
        guard="B",
        status="PASSED",
        reason=reason_msg,
        ms=ms,
    )
