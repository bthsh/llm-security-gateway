import base64
import re
import time
import unicodedata
from urllib.parse import unquote
from app.models import RequestContext, StageResult, Finding

# Invisible characters regex: zero-width spaces/joiners, BOM, tag chars
INVISIBLE_CHARS_RE = re.compile(
    r"[\u200B-\u200D\u2060\uFEFF\U000E0000-\U000E007F]"
)

# Common Homoglyph mappings (Cyrillic/Greek to Latin lookalikes) for detection copy
HOMOGLYPH_MAP = str.maketrans(
    {
        "а": "a",
        "А": "A",
        "е": "e",
        "Е": "E",
        "о": "o",
        "О": "O",
        "р": "p",
        "Р": "P",
        "с": "c",
        "С": "C",
        "у": "y",
        "У": "Y",
        "х": "x",
        "Х": "X",
        "і": "i",
        "І": "I",
        "α": "a",
        "ο": "o",
        "ν": "v",
    }
)

BASE64_RE = re.compile(r"\b[A-Za-z0-9+/]{12,}={0,2}(?!\w)")
HEX_RE = re.compile(r"\b(?:0x)?[0-9a-fA-F]{32,}\b")


def normalize_text(text: str) -> tuple[str, bool, list[str]]:
    reasons = []
    changed = False

    # 1. NFKC Normalization
    normalized = unicodedata.normalize("NFKC", text)
    if normalized != text:
        changed = True
        reasons.append("NFKC normalized")

    # 2. Strip invisible characters
    cleaned = INVISIBLE_CHARS_RE.sub("", normalized)
    if cleaned != normalized:
        changed = True
        reasons.append("Zero-width/invisible characters removed")

    # 3. Homoglyph mapping for detection
    det_text = cleaned.translate(HOMOGLYPH_MAP)

    # 4. Decodings (Base64, URL encoding, Hex)
    # URL Decoding
    url_decoded = unquote(cleaned)
    if url_decoded != cleaned:
        changed = True
        reasons.append("URL-encoded content decoded")
        det_text += f"\n[DECODED_URL: {url_decoded}]"

    # Base64 Decoding
    for match in BASE64_RE.finditer(cleaned):
        raw = match.group(0)
        try:
            decoded_bytes = base64.b64decode(raw)
            decoded_str = decoded_bytes.decode("utf-8", errors="ignore").strip()
            if len(decoded_str) > 5 and any(c.isalnum() for c in decoded_str):
                changed = True
                reasons.append("Base64 payload decoded")
                det_text += f"\n[DECODED_BASE64: {decoded_str}]"
        except Exception:
            pass

    # Hex Decoding
    for match in HEX_RE.finditer(cleaned):
        raw = match.group(0).replace("0x", "")
        try:
            decoded_bytes = bytes.fromhex(raw)
            decoded_str = decoded_bytes.decode("utf-8", errors="ignore").strip()
            if len(decoded_str) > 5 and any(c.isalnum() for c in decoded_str):
                changed = True
                reasons.append("Hex payload decoded")
                det_text += f"\n[DECODED_HEX: {decoded_str}]"
        except Exception:
            pass

    return det_text, changed, reasons


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    findings = []
    any_changed = False
    all_reasons = []

    try:
        for seg in ctx.segments:
            norm_text, changed, reasons = normalize_text(seg.text)
            if changed:
                any_changed = True
                all_reasons.extend(reasons)
                findings.append(
                    Finding(
                        rule_id="normalize.obfuscation",
                        score=0.5,
                        reason=", ".join(reasons),
                        owasp="LLM01",
                    )
                )
            seg.text = norm_text

        ms = (time.perf_counter() - start_t) * 1000.0
        status = "FLAGGED" if any_changed else "PASSED"
        reason_str = (
            ", ".join(set(all_reasons)) if any_changed else "No hidden encoding"
        )

        return StageResult(
            step=1,
            name="normalize",
            guard="A",
            status=status,
            reason=reason_str,
            ms=ms,
            findings=findings,
        )
    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=1,
            name="normalize",
            guard="A",
            status="ERROR",
            reason=f"Error in normalize: {e}",
            ms=ms,
        )
