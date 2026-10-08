import time
from app.config import load_profile, settings
from app.models import RequestContext, StageResult, BeforeAfterItem


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    try:
        profile_data = load_profile(ctx.profile)
        thresholds = profile_data.get("thresholds", {})
        user_block = thresholds.get("user", {}).get("block", 0.80)
        user_low = thresholds.get("user", {}).get("borderline_low", 0.50)
        untrusted_remove = thresholds.get("untrusted", {}).get("remove", 0.80)
        untrusted_low = thresholds.get("untrusted", {}).get(
            "borderline_low", 0.40
        )

        seg_map = {s.id: s for s in ctx.segments}
        request_blocked = False
        any_cleaned = False
        block_reason = ""

        # 1. Decide per chunk
        for chunk in ctx.chunks:
            seg = seg_map.get(chunk.segment_id)
            if not seg:
                continue

            if seg.trust == "trusted":
                if chunk.score >= user_block:
                    request_blocked = True
                    block_reason = f"User message blocked (risk score {chunk.score:.2f} >= {user_block})"
                    chunk.action = "remove"
                elif chunk.score >= user_low:
                    # Session tainted for borderline user message
                    pass
                else:
                    chunk.action = "keep"
            else:
                # Untrusted chunk decision
                if chunk.score >= untrusted_low:
                    chunk.action = "remove"
                    any_cleaned = True
                else:
                    chunk.action = "keep"

        # 2. Early Exit check
        if request_blocked:
            ctx.decision = "BLOCKED"
            ctx.decision_reason = block_reason
            ms = (time.perf_counter() - start_t) * 1000.0
            return StageResult(
                step=5,
                name="decide",
                guard="A",
                status="BLOCKED",
                reason=block_reason,
                ms=ms,
            )

        # 3. Document drop ratio & Before/After generation
        before_after_list = []
        for seg in ctx.segments:
            seg_chunks = [c for c in ctx.chunks if c.segment_id == seg.id]
            if not seg_chunks:
                continue

            removed_chunks = [c for c in seg_chunks if c.action == "remove"]
            kept_chunks = [c for c in seg_chunks if c.action != "remove"]
            drop_ratio = (
                len(removed_chunks) / len(seg_chunks) if seg_chunks else 0.0
            )

            kept_text_parts = [c.text for c in kept_chunks]
            kept_text_len = len(" ".join(kept_text_parts).strip())
            removed_items = []

            if (
                seg.trust == "untrusted"
                and drop_ratio > settings.DOC_DROP_RATIO
                and kept_text_len < 50
            ):
                # Drop entire document
                removed_items.append(
                    {
                        "text": seg.text,
                        "reason": f"Entire file dropped (removal ratio {drop_ratio:.2f} > {settings.DOC_DROP_RATIO} and visible text < 50 chars)",
                        "hidden": False,
                    }
                )
                any_cleaned = True
                seg.text = ""
            else:
                for c in seg_chunks:
                    if c.action == "remove":
                        removed_items.append(
                            {
                                "text": c.text,
                                "reason": f"Flagged chunk removed (score {c.score:.2f})",
                                "hidden": c.is_hidden,
                            }
                        )

                seg.text = " ".join(kept_text_parts)

            if removed_items:
                before_after_list.append(
                    BeforeAfterItem(
                        origin=seg.origin,
                        source=seg.source,
                        kept_text=" ".join(kept_text_parts),
                        removed=removed_items,
                    )
                )

        ctx.before_after = before_after_list

        if any_cleaned:
            ctx.decision = "CLEANED"
            ctx.decision_reason = "Flagged untrusted content removed"
            status = "CLEANED"
            reason = "Untrusted chunks cleaned"
        else:
            ctx.decision = "ALLOWED"
            ctx.decision_reason = "Passed Guard A checks"
            status = "PASSED"
            reason = "No content removed"

        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=5,
            name="decide",
            guard="A",
            status=status,
            reason=reason,
            ms=ms,
        )

    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=5,
            name="decide",
            guard="A",
            status="ERROR",
            reason=f"Error in decide: {e}",
            ms=ms,
        )
