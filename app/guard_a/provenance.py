import time
from app.models import RequestContext, StageResult


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    try:
        sources_summary = []
        has_untrusted = False

        for seg in ctx.segments:
            if seg.source in ("system", "user"):
                seg.trust = "trusted"
            else:
                seg.trust = "untrusted"
                has_untrusted = True

            sources_summary.append(f"{seg.source}={seg.trust}")

        ms = (time.perf_counter() - start_t) * 1000.0
        reason_str = (
            ", ".join(sources_summary)
            if sources_summary
            else "No segments to tag"
        )

        return StageResult(
            step=3,
            name="provenance",
            guard="A",
            status="INFO",
            reason=reason_str,
            ms=ms,
        )
    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=3,
            name="provenance",
            guard="A",
            status="ERROR",
            reason=f"Error in provenance: {e}",
            ms=ms,
        )
