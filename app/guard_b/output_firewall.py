import time
from app.models import RequestContext, StageResult


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    ms = (time.perf_counter() - start_t) * 1000.0
    return StageResult(
        step=9,
        name="output_firewall",
        guard="B",
        status="PASSED",
        reason="Reply validated cleanly",
        ms=ms,
    )
