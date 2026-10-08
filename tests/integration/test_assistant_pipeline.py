from app.llm.base import LLMResult, ToolCallRequest
from app.models import RequestContext, Segment
from app.assistant.loop import run_assistant_loop


class FakeScriptedBackend:

    def __init__(
        self,
        reply: str = "Test response",
        tool_calls: list[ToolCallRequest] | None = None,
    ):
        self.reply = reply
        self.tool_calls = tool_calls or []
        self.called = False

    def generate(self, system, messages, tools):
        if not self.called and self.tool_calls:
            self.called = True
            return LLMResult(
                text=None, tool_calls=self.tool_calls, model="fake"
            )
        return LLMResult(text=self.reply, tool_calls=[], model="fake")


def test_scripted_tool_execution():
    backend = FakeScriptedBackend(
        tool_calls=[
            ToolCallRequest(
                name="lookup_record", args={"record_id": "ORD-1001"}
            )
        ]
    )
    ctx = RequestContext(
        request_id="req_test",
        session_id="sess_test",
        profile="customer_support",
        offered_tools=["lookup_record"],
        segments=[
            Segment(
                id="s1",
                source="user",
                trust="trusted",
                text="Where is my order ORD-1001?",
            )
        ],
    )

    ctx = run_assistant_loop(ctx, backend=backend)

    assert len(ctx.tool_calls) == 1
    assert ctx.tool_calls[0].tool == "lookup_record"
    assert ctx.tool_calls[0].status == "EXECUTED"
    assert "Alice Smith" in ctx.reply or ctx.reply == "Test response"


def test_policy_blocked_tool_call():
    # Attempting to read path outside directory
    backend = FakeScriptedBackend(
        tool_calls=[
            ToolCallRequest(
                name="read_document", args={"name": "../../.env"}
            )
        ]
    )
    ctx = RequestContext(
        request_id="req_test",
        session_id="sess_test",
        profile="customer_support",
        offered_tools=["read_document"],
        segments=[
            Segment(
                id="s1",
                source="user",
                trust="trusted",
                text="Read the env document file",
            )
        ],
    )

    ctx = run_assistant_loop(ctx, backend=backend)

    assert len(ctx.tool_calls) == 1
    assert ctx.tool_calls[0].status == "BLOCKED"
    assert "Path traversal" in ctx.tool_calls[0].reason
