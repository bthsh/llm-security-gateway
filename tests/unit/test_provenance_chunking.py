from app.guard_a.provenance import run as run_provenance
from app.guard_a.chunking import build_chunks_for_context, split_text_into_chunks
from app.models import RequestContext, Segment


def test_provenance_trust_tagging():
    ctx = RequestContext(
        request_id="req_test",
        session_id="sess_test",
        profile="customer_support",
        segments=[
            Segment(id="s1", source="user", trust="trusted", text="Hello"),
            Segment(id="s2", source="email", trust="untrusted", text="Injected email text"),
        ],
    )
    result = run_provenance(ctx)
    assert result.status == "INFO"
    assert ctx.segments[0].trust == "trusted"
    assert ctx.segments[1].trust == "untrusted"


def test_chunking_sentence_splitting():
    long_text = "Sentence one. " * 150
    chunks = split_text_into_chunks(long_text, max_chars=1000)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 1200


def test_build_chunks_with_hidden_text():
    ctx = RequestContext(
        request_id="req_test",
        session_id="sess_test",
        profile="customer_support",
        segments=[
            Segment(
                id="s1",
                source="document",
                trust="untrusted",
                text="Visible document body",
                hidden_text="Hidden prompt injection instruction",
            )
        ],
    )
    chunks = build_chunks_for_context(ctx)
    assert len(chunks) == 2
    assert chunks[0].is_hidden is False
    assert chunks[1].is_hidden is True
    assert chunks[1].text == "Hidden prompt injection instruction"


def test_untrusted_attachment_taints_session_and_hides_send_email():
    from app.guard_a.canary_tools import run as run_canary_tools
    from app.sessions import get_session

    ctx = RequestContext(
        request_id="req_taint_test",
        session_id="sess_taint_test",
        profile="customer_support",
        segments=[
            Segment(id="s1", source="user", trust="trusted", text="Summarize this file"),
            Segment(id="s2", source="email", trust="untrusted", text="Poisoned email text"),
        ],
    )
    # Step 3 provenance
    run_provenance(ctx)
    session = get_session("sess_taint_test")
    assert session.taint is True

    # Step 7 canary_tools
    run_canary_tools(ctx)
    assert "send_email" in ctx.hidden_tools
    assert "send_email" not in ctx.offered_tools


def test_s13_risky_tool_hidden_when_session_tainted():
    # S-13: Risky tool with tainted session (tool hidden at step 7)
    from app.guard_a.canary_tools import run as run_canary_tools
    from app.sessions import get_session

    sess_id = "sess_s13_test"
    session = get_session(sess_id)
    session.taint = True

    ctx = RequestContext(
        request_id="req_s13",
        session_id=sess_id,
        profile="customer_support",
        segments=[
            Segment(id="s1", source="user", trust="trusted", text="Send an email to john")
        ],
    )
    result = run_canary_tools(ctx)
    assert result.status == "INFO"
    assert "send_email" in ctx.hidden_tools
    assert "send_email" not in ctx.offered_tools


