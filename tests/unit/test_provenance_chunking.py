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
