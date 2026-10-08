from typing import Literal, Any
from pydantic import BaseModel, Field

Source = Literal["system", "user", "document", "web", "email", "tool_result"]
Trust = Literal["trusted", "untrusted"]
StepStatus = Literal[
    "PASSED", "FLAGGED", "CLEANED", "BLOCKED", "SKIPPED", "INFO", "LOGGED", "ERROR"
]
RequestDecision = Literal[
    "ALLOWED", "CLEANED", "BLOCKED", "BLOCKED_ACTION", "NEEDS_APPROVAL"
]
ToolCallStatus = Literal[
    "EXECUTED", "BLOCKED", "PENDING_APPROVAL", "APPROVED", "DENIED"
]


class Segment(BaseModel):
    id: str
    source: Source
    trust: Trust
    text: str
    visible_text: str | None = None
    hidden_text: str | None = None
    origin: str | None = None


class Chunk(BaseModel):
    id: str
    segment_id: str
    text: str
    is_hidden: bool = False
    score: float = 0.0
    action: Literal["keep", "remove"] = "keep"
    reasons: list[str] = Field(default_factory=list)


class Finding(BaseModel):
    rule_id: str
    score: float
    reason: str
    owasp: str | None = None


class StageResult(BaseModel):
    step: int | str
    name: str
    guard: Literal["A", "B", "-"]
    status: StepStatus
    reason: str
    ms: float = 0.0
    findings: list[Finding] = Field(default_factory=list)


class ToolCall(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    status: ToolCallStatus = "EXECUTED"
    reason: str = ""


class PendingAction(BaseModel):
    id: str
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)
    reason: str


class BeforeAfterItem(BaseModel):
    origin: str | None = None
    source: Source
    kept_text: str
    removed: list[dict[str, Any]] = Field(default_factory=list)


class RedactionItem(BaseModel):
    type: str
    preview: str
    replacement: str


class LayerSettings(BaseModel):
    classifier: bool = True
    judge: bool = True
    tool_scoping: bool = True
    policy_engine: bool = True
    output_firewall: bool = True


class RequestContext(BaseModel):
    request_id: str
    session_id: str
    profile: str
    layers: LayerSettings = Field(default_factory=LayerSettings)
    segments: list[Segment] = Field(default_factory=list)
    chunks: list[Chunk] = Field(default_factory=list)
    nonce: str = ""
    canary: str = ""
    offered_tools: list[str] = Field(default_factory=list)
    hidden_tools: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    reply: str | None = None
    decision: RequestDecision = "ALLOWED"
    decision_reason: str = ""
    trace: list[StageResult] = Field(default_factory=list)
    timings: dict[str, float] = Field(default_factory=dict)
    before_after: list[BeforeAfterItem] = Field(default_factory=list)
    pending_action: PendingAction | None = None
    outbox: list[dict[str, Any]] = Field(default_factory=list)
    redactions: list[RedactionItem] = Field(default_factory=list)


class ChatResponse(BaseModel):
    request_id: str
    session_id: str
    profile: str
    decision: RequestDecision
    decision_reason: str
    reply: str
    trace: list[StageResult]
    before_after: list[BeforeAfterItem] = Field(default_factory=list)
    hidden_tools: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    pending_action: PendingAction | None = None
    outbox: list[dict[str, Any]] = Field(default_factory=list)
    redactions: list[RedactionItem] = Field(default_factory=list)
    timings: dict[str, float]
    layers: LayerSettings
