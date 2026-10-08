import re
import time
from app.config import load_profile, load_pii_rules
from app.models import RequestContext, StageResult, RedactionItem

CANARY_REGEX = re.compile(r"CANARY_[0-9a-f]{12}")
INLINE_IMAGE_RE = re.compile(r"!\[.*?\]\(.*?\)")
REF_IMAGE_DEF_RE = re.compile(r"^\s*\[.*?\]:\s*https?://\S+", re.MULTILINE)
REF_IMAGE_USAGE_RE = re.compile(r"!\[.*?\]\[.*?\]")
HTML_IMG_RE = re.compile(r"<img\s+[^>]*>", re.IGNORECASE)
MARKDOWN_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\)]+)\)")


def mask_preview(val: str) -> str:
    if "@" in val:
        parts = val.split("@")
        user = parts[0]
        domain = parts[1] if len(parts) > 1 else ""
        masked_user = user[0] + "***" if len(user) > 0 else "***"
        return f"{masked_user}@{domain}"
    if len(val) > 4:
        return val[:2] + "*" * (len(val) - 4) + val[-2:]
    return "***"


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    try:
        if not ctx.reply:
            ms = (time.perf_counter() - start_t) * 1000.0
            return StageResult(
                step=9,
                name="output_firewall",
                guard="B",
                status="PASSED",
                reason="No reply text to scan",
                ms=ms,
            )

        reply_text = ctx.reply

        # 1. Canary check
        if (ctx.canary and ctx.canary in reply_text) or CANARY_REGEX.search(
            reply_text
        ):
            ctx.reply = "[WITHHELD] Security policy blocked output containing internal reference tokens."
            ctx.decision = "BLOCKED"
            ctx.decision_reason = "System prompt canary leaked in reply"
            ms = (time.perf_counter() - start_t) * 1000.0
            return StageResult(
                step=9,
                name="output_firewall",
                guard="B",
                status="BLOCKED",
                reason="System prompt canary leak detected (LLM07)",
                ms=ms,
            )

        if not ctx.layers.output_firewall:
            ms = (time.perf_counter() - start_t) * 1000.0
            return StageResult(
                step=9,
                name="output_firewall",
                guard="B",
                status="PASSED",
                reason="Output firewall layer off (demo mode)",
                ms=ms,
            )

        profile_data = load_profile(ctx.profile)
        output_cfg = profile_data.get("output", {})
        allowed_link_domains = output_cfg.get("allowed_link_domains", [])
        redaction_allowlist = output_cfg.get("redaction_allowlist", [])

        # 3. Links and images removal
        reply_text = INLINE_IMAGE_RE.sub("", reply_text)
        reply_text = REF_IMAGE_USAGE_RE.sub("", reply_text)
        reply_text = REF_IMAGE_DEF_RE.sub("", reply_text)
        reply_text = HTML_IMG_RE.sub("", reply_text)

        # Disallowed link stripping
        def filter_link(match):
            text = match.group(1)
            url = match.group(2)
            domain = url.split("/")[2] if "//" in url else ""
            if domain in allowed_link_domains:
                return match.group(0)
            return text  # keep link text, drop URL

        reply_text = MARKDOWN_LINK_RE.sub(filter_link, reply_text)

        # 4. Redaction
        pii_rules = load_pii_rules()
        redactions = []

        for pii in pii_rules:
            pattern_str = pii.get("pattern")
            replacement = pii.get("replacement")
            rule_id = pii.get("id")

            if not pattern_str or not replacement:
                continue

            for match in re.finditer(pattern_str, reply_text):
                val = match.group(0)
                if val in redaction_allowlist:
                    continue

                redactions.append(
                    RedactionItem(
                        type=rule_id,
                        preview=mask_preview(val),
                        replacement=replacement,
                    )
                )

            reply_text = re.sub(pattern_str, replacement, reply_text)

        ctx.reply = reply_text
        ctx.redactions = redactions

        ms = (time.perf_counter() - start_t) * 1000.0
        status = "CLEANED" if redactions else "PASSED"
        reason_msg = (
            f"Applied {len(redactions)} redactions"
            if redactions
            else "Reply passed output firewall"
        )

        return StageResult(
            step=9,
            name="output_firewall",
            guard="B",
            status=status,
            reason=reason_msg,
            ms=ms,
        )

    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=9,
            name="output_firewall",
            guard="B",
            status="ERROR",
            reason=f"Error in output firewall: {e}",
            ms=ms,
        )
