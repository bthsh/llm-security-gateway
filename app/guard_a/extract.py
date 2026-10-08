import email
import io
import re
import time
from email.message import Message
from bs4 import BeautifulSoup, Comment
import pypdf
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar

from app.config import settings
from app.models import RequestContext, StageResult, Segment


def extract_html(html_str: str) -> tuple[str, str]:
    soup = BeautifulSoup(html_str, "html.parser")

    hidden_parts = []

    # 1. HTML Comments
    comments = soup.find_all(string=lambda text: isinstance(text, Comment))
    for c in comments:
        hidden_parts.append(str(c).strip())
        c.extract()

    # 2. Meta tags
    meta_tags = soup.find_all("meta")
    for m in meta_tags:
        content = m.get("content")
        if content:
            hidden_parts.append(f"Meta tag: {content}")
        m.extract()

    # 3. Elements with hidden inline styles / attributes
    for el in soup.find_all(True):
        style = el.get("style", "").lower()
        has_hidden_attr = el.has_attr("hidden")
        
        is_hidden_style = (
            "display:none" in style
            or "visibility:hidden" in style
            or "opacity:0" in style
            or "font-size:0" in style
            or "font-size:1px" in style
            or "left:-" in style
            or "color:#fff" in style
            or "color:white" in style
        )

        if is_hidden_style or has_hidden_attr:
            el_text = el.get_text(strip=True)
            if el_text:
                hidden_parts.append(el_text)
            el.extract()

    # Visible text remaining in clean DOM
    visible_text = soup.get_text(separator=" ", strip=True)
    hidden_text = "\n".join(hidden_parts)

    return visible_text, hidden_text


def extract_pdf(content_bytes: bytes) -> tuple[str, str]:
    visible_parts = []
    hidden_parts = []

    # PyPDF annotations & metadata
    reader = pypdf.PdfReader(io.BytesIO(content_bytes))
    
    if reader.metadata:
        for k, v in reader.metadata.items():
            if v and isinstance(v, str) and len(v.strip()) > 0:
                hidden_parts.append(f"PDF Metadata {k}: {v.strip()}")

    for i, page in enumerate(reader.pages):
        # Extract page annotations
        if page.annotations:
            for annot in page.annotations:
                obj = annot.get_object()
                text = obj.get("/Contents")
                if text:
                    hidden_parts.append(f"PDF Annotation: {text}")

    # pdfminer font size & color check
    try:
        pages = list(extract_pages(io.BytesIO(content_bytes)))
        for page_layout in pages:
            for element in page_layout:
                if isinstance(element, LTTextContainer):
                    for text_line in element:
                        line_text = text_line.get_text().strip()
                        if not line_text:
                            continue
                        
                        # Check font size of chars in line
                        is_tiny = False
                        for char in text_line:
                            if isinstance(char, LTChar):
                                if char.size < 2.0:
                                    is_tiny = True
                                    break
                        
                        if is_tiny:
                            hidden_parts.append(f"Tiny font text (<2pt): {line_text}")
                        else:
                            visible_parts.append(line_text)
    except Exception:
        # Fallback to PyPDF text extraction
        for page in reader.pages:
            t = page.extract_text()
            if t:
                visible_parts.append(t)

    visible_text = "\n".join(visible_parts)
    hidden_text = "\n".join(hidden_parts)

    return visible_text, hidden_text


def extract_email(content_bytes: bytes) -> tuple[str, str]:
    msg: Message = email.message_from_bytes(content_bytes)

    plain_part = ""
    html_part = ""
    hidden_parts = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if "attachment" in content_disposition:
                continue

            payload = part.get_payload(decode=True)
            if not payload:
                continue

            if content_type == "text/plain":
                plain_part += payload.decode("utf-8", errors="ignore") + "\n"
            elif content_type == "text/html":
                html_part += payload.decode("utf-8", errors="ignore") + "\n"
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            content_type = msg.get_content_type()
            if content_type == "text/html":
                html_part = payload.decode("utf-8", errors="ignore")
            else:
                plain_part = payload.decode("utf-8", errors="ignore")

    visible_html, hidden_html = "", ""
    if html_part:
        visible_html, hidden_html = extract_html(html_part)
        if hidden_html:
            hidden_parts.append(hidden_html)

    # Decision D-28: Sentence diff between plain part and HTML part
    # Any sentence present in HTML but missing from plain text becomes hidden_text
    if plain_part and html_part:
        norm_plain = " ".join(plain_part.split())
        plain_sentences = set(
            s.strip().lower()
            for s in re.split(r"(?<=[.!?])\s+", norm_plain)
            if s.strip()
        )

        norm_html_vis = " ".join(visible_html.split())
        html_sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", norm_html_vis)
            if s.strip()
        ]

        for s in html_sentences:
            if s.lower() not in plain_sentences and len(s) > 10:
                hidden_parts.append(f"HTML sentence missing from plain text: {s}")

    visible_text = plain_part.strip() if plain_part.strip() else visible_html.strip()
    hidden_text = "\n".join(hidden_parts)

    return visible_text, hidden_text


def run(ctx: RequestContext) -> StageResult:
    start_t = time.perf_counter()
    findings = []
    any_hidden = False
    has_error = False
    error_msgs = []

    try:
        for seg in ctx.segments:
            if seg.trust == "untrusted" and seg.origin:
                origin_lower = seg.origin.lower()
                text_bytes = seg.text.encode("utf-8")

                try:
                    if origin_lower.endswith(".pdf"):
                        vis, hid = extract_pdf(text_bytes)
                        seg.visible_text = vis
                        seg.hidden_text = hid
                        seg.text = vis
                    elif origin_lower.endswith(".html") or origin_lower.endswith(".htm"):
                        vis, hid = extract_html(seg.text)
                        seg.visible_text = vis
                        seg.hidden_text = hid
                        seg.text = vis
                    elif origin_lower.endswith(".eml"):
                        vis, hid = extract_email(text_bytes)
                        seg.visible_text = vis
                        seg.hidden_text = hid
                        seg.text = vis

                    if seg.hidden_text and seg.hidden_text.strip():
                        any_hidden = True
                except Exception as e:
                    has_error = True
                    error_msgs.append(f"Extractor error on '{seg.origin}': {e}")
                    # Decision D-32: Drop content on extractor error, fail-closed
                    seg.text = ""
                    seg.visible_text = ""
                    seg.hidden_text = ""

        ms = (time.perf_counter() - start_t) * 1000.0

        if has_error:
            return StageResult(
                step=2,
                name="extract",
                guard="A",
                status="ERROR",
                reason=", ".join(error_msgs),
                ms=ms,
            )

        status = "FLAGGED" if any_hidden else "PASSED"
        reason = "Hidden text found in attachment" if any_hidden else "No hidden text found"

        return StageResult(
            step=2,
            name="extract",
            guard="A",
            status=status,
            reason=reason,
            ms=ms,
        )

    except Exception as e:
        ms = (time.perf_counter() - start_t) * 1000.0
        return StageResult(
            step=2,
            name="extract",
            guard="A",
            status="ERROR",
            reason=f"Extractor error: {e}",
            ms=ms,
        )
