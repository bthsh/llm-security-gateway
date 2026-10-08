import time
from app.config import settings, load_profile
from app.guard_a.classifier import classifier
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

        # Batch classifier evaluation if classifier layer is on
        chunk_texts_for_cls = []
        indices_for_cls = []

        for i, chunk in enumerate(ctx.chunks):
            rule_score, _ = rule_engine.evaluate_chunk(chunk)
            # Only run classifier if rules didn't already score >= 0.80 (saves time)
            if ctx.layers.classifier and rule_score < 0.80:
                chunk_texts_for_cls.append(chunk.text)
                indices_for_cls.append(i)

        classifier_scores = [0.0] * len(ctx.chunks)
        if chunk_texts_for_cls:
            cls_preds = classifier.predict_batch(chunk_texts_for_cls)
            for idx, prob in zip(indices_for_cls, cls_preds):
                classifier_scores[idx] = prob

        for i, chunk in enumerate(ctx.chunks):
            # 1. Evaluate rules
            rule_score, chunk_findings = rule_engine.evaluate_chunk(chunk)
            findings.extend(chunk_findings)

            # 2. Classifier score
            cls_score = classifier_scores[i]

            # Narrowed heuristic for trusted user prompts with Hard Veto List & 0.45 Cap
            seg_map_tmp = {s.id: s for s in ctx.segments}
            chunk_seg = seg_map_tmp.get(chunk.segment_id)
            if chunk_seg and chunk_seg.trust == "trusted" and rule_score == 0.0:
                import re
                from app.sessions import get_session

                veto_patterns = [
                    r"(?i)\b(your|the|all|any|previous|prior|above)\s+(instructions|system prompt|rules|guidelines)\b",
                    r"(?i)\b(system prompt|canary|api key|credentials)\b",
                    r"(?i)\b(repeat|reveal|print|show|display)\b.{0,30}\b(instructions|prompt|above|system)\b",
                    r"(?i)\b(override|bypass|disregard|ignore)\b.{0,30}\b(system|instruction|rule|guideline|restriction)\b",
                    r"(?i)\b(then do it|now do it|execute that|follow that)\b",
                ]

                narrow_safe_patterns = [
                    r"(?i)\bignore (my |the )?(last |previous |prior )?(order|email|message|item|request|invoice)\b",
                    r"(?i)\bdisregard (the |my )?(last |previous |prior )?(invoice|receipt|order|payment|email|message)\b",
                ]

                # Check unallowed email domains
                allowed_email_domains = (
                    profile_data.get("tools", {})
                    .get("send_email", {})
                    .get("allowed_email_domains", ["examplefoods.example"])
                )
                email_matches = re.findall(
                    r"[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
                    chunk.text,
                )
                has_unallowed_email = any(
                    dom.lower() not in [d.lower() for d in allowed_email_domains]
                    for dom in email_matches
                )

                has_veto = (
                    any(re.search(vp, chunk.text) for vp in veto_patterns)
                    or has_unallowed_email
                )
                is_short = len(chunk.text.strip()) < 200
                matches_safe = any(
                    re.search(sp, chunk.text) for sp in narrow_safe_patterns
                )

                # Check if multi-sentence chunk has any sentence scoring >= 0.50
                second_sentence_high = False
                sentences = [
                    s.strip()
                    for s in re.split(r"(?<=[.!?])\s+", chunk.text.strip())
                    if s.strip()
                ]
                if len(sentences) > 1:
                    sent_scores = classifier.predict_batch(sentences)
                    if any(s_sc >= 0.50 for s_sc in sent_scores):
                        second_sentence_high = True

                if (
                    not has_veto
                    and is_short
                    and matches_safe
                    and not second_sentence_high
                ):
                    cls_score = min(cls_score, 0.45)
                    session = get_session(ctx.session_id)
                    session.taint = True

            if cls_score >= 0.50:
                findings.append(
                    Finding(
                        rule_id="classifier",
                        score=cls_score,
                        reason=f"Classifier score {cls_score:.2f} >= 0.50",
                        owasp="LLM01",
                    )
                )

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
                1.0, max(rule_score, cls_score) + hidden_bonus
            )
            chunk.score = final_score
            if final_score > top_score:
                top_score = final_score

            # Populate chunk reasons
            chunk.reasons = [f.reason for f in chunk_findings]
            if cls_score >= 0.50:
                chunk.reasons.append(f"Classifier score: {cls_score:.2f}")
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
