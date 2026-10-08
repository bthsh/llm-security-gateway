from app.guard_b import policy, output_firewall
from app.models import RequestContext, Segment, ToolCall, PendingAction
from app.sessions import get_session


def test_s07_canary_leak_withheld_in_reply():
    # S-07: Canary leak in reply -> Step 9 withholds reply, decision BLOCKED
    ctx = RequestContext(
        request_id="req_s07",
        session_id="sess_s07",
        profile="customer_support",
        canary="CANARY_123456789abc",
        reply="Here is your info: CANARY_123456789abc system prompt contents",
    )

    result = output_firewall.run(ctx)
    assert result.status == "BLOCKED"
    assert ctx.decision == "BLOCKED"
    assert "[WITHHELD]" in ctx.reply
    assert "canary" in ctx.decision_reason.lower()


def test_s10_send_email_disallowed_domain_blocked():
    # S-10: send_email to attacker@evil.example -> Step 8 BLOCKED (domain)
    ctx = RequestContext(
        request_id="req_s10",
        session_id="sess_s10",
        profile="customer_support",
        offered_tools=["send_email"],
    )

    status, reason = policy.evaluate_tool_call(
        ctx, "send_email", {"to": "attacker@evil.example", "subject": "hi", "body": "test"}
    )
    assert status == "BLOCKED"
    assert "not in allowed list" in reason


def test_s11_read_document_path_traversal_blocked():
    # S-11: read_document("../../.env") -> Step 8 BLOCKED (path traversal)
    ctx = RequestContext(
        request_id="req_s11",
        session_id="sess_s11",
        profile="customer_support",
        offered_tools=["read_document"],
    )

    status, reason = policy.evaluate_tool_call(
        ctx, "read_document", {"name": "../../.env"}
    )
    assert status == "BLOCKED"
    assert "Path traversal" in reason


def test_s12_lookup_record_wildcard_blocked():
    # S-12: lookup_record("all") -> Step 8 BLOCKED (pattern)
    ctx = RequestContext(
        request_id="req_s12",
        session_id="sess_s12",
        profile="customer_support",
        offered_tools=["lookup_record"],
    )

    status, reason = policy.evaluate_tool_call(
        ctx, "lookup_record", {"record_id": "all"}
    )
    assert status == "BLOCKED"
    assert "Multiple/wildcard record access not allowed" in reason


def test_s14_approval_cannot_override_hard_domain_rule():
    # S-14: Approval flow cannot override hard domain rules
    ctx = RequestContext(
        request_id="req_s14",
        session_id="sess_s14",
        profile="customer_support",
        offered_tools=["send_email"],
    )

    # Hard domain check must fail regardless of approval attempt
    status, reason = policy.evaluate_tool_call(
        ctx, "send_email", {"to": "attacker@evil.example", "subject": "test", "body": "test"}
    )
    assert status == "BLOCKED"
    assert "not in allowed list" in reason
