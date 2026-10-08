import secrets
import time
from app.models import RequestContext, StageResult


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    try:
        ctx.nonce = f"data_{secrets.token_hex(4)}"

        for seg in ctx.segments:
            if seg.trust == "untrusted" and seg.text and seg.text.strip():
                # Escape forged tag attempts inside text
                escaped_text = seg.text.replace("<data_", "&lt;data_").replace(
                    ">", "&gt;"
                )
                seg.text = (
                    f"<{ctx.nonce} source=\"{seg.source}\" origin=\"{seg.origin or 'unknown'}\">\n"
                    f"{escaped_text}\n"
                    f"</{ctx.nonce}>"
                )

        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=6,
            name="spotlight",
            guard="A",
            status="INFO",
            reason=f"Wrapped untrusted text with nonce {ctx.nonce}",
            ms=ms,
        )
    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=6,
            name="spotlight",
            guard="A",
            status="ERROR",
            reason=f"Error in spotlight: {e}",
            ms=ms,
        )
