import time
from app.config import settings, load_profile
from app.guard_a.rules import rule_engine
from app.models import RequestContext, StageResult, Finding


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    findings: list[Finding] = []
    top_score = 0.0

    try:
        profile_data = load_profile(ctx.profile)
        thresholds = profile_data.get("thresholds", {})
        user_low = thresholds.get("user", {}).get("borderline_low", 0.50)
        untrusted_low = thresholds.get("untrusted", {}).get(
            "borderline_low", 0.40
        )

        for chunk in ctx.chunks:
            # 1. Evaluate rules
            rule_score, chunk_findings = rule_engine.evaluate_chunk(chunk)
            findings.extend(chunk_findings)

            # 2. Classifier score (0.0 in basic detect; classifier module can update it)
            classifier_score = 0.0

            # 3. Hidden text bonus
            hidden_bonus = (
                settings.HIDDEN_TEXT_BONUS if chunk.is_hidden else 0.0
            )
            if chunk.is_hidden:
                findings.append(
                    Finding(
                        rule_id="hidden_text",
                        score=settings.HIDDEN_TEXT_BONUS,
                        reason="Chunk contains hidden text extracted from attachment",
                        owasp="LLM01",
                    )
                )

            # Total score
            final_score = min(
                1.0, max(rule_score, classifier_score) + hidden_bonus
            )
            chunk.score = final_score
            if final_score > top_score:
                top_score = final_score

            # Populate chunk reasons
            chunk.reasons = [f.reason for f in chunk_findings]
            if chunk.is_hidden:
                chunk.reasons.append("Hidden text bonus +0.30")

        # Find segment owner for threshold check
        seg_map = {s.id: s for s in ctx.segments}
        is_flagged = False

        for chunk in ctx.chunks:
            seg = seg_map.get(chunk.segment_id)
            threshold = (
                user_low if (seg and seg.trust == "trusted") else untrusted_low
            )
            if chunk.score >= threshold:
                is_flagged = True
                break

        ms = (time.perf_counter() - start_t) * 1000.0
        status = "FLAGGED" if is_flagged else "PASSED"
        reason_str = (
            f"Top risk score: {top_score:.2f}"
            if ctx.chunks
            else "No chunks to score"
        )

        return StageResult(
            step=4,
            name="detect",
            guard="A",
            status=status,
            reason=reason_str,
            ms=ms,
            findings=findings,
        )
    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=4,
            name="detect",
            guard="A",
            status="ERROR",
            reason=f"Error in detect: {e}",
            ms=ms,
        )
