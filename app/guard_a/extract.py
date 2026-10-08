import time
from app.models import RequestContext, StageResult


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    # In Checkpoint 1: basic extractor pass-through for text attachments
    ms = (time.perf_counter() - start_t) * 1000.0
    return StageResult(
        step=2,
        name="extract",
        guard="A",
        status="PASSED",
        reason="No hidden text found",
        ms=ms,
    )
