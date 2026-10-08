from pydantic import BaseModel, Field
from app.models import LayerSettings, PendingAction, Segment


class SessionData(BaseModel):
    session_id: str
    taint: bool = False
    layers: LayerSettings = Field(default_factory=LayerSettings)
    pending_action: PendingAction | None = None
    outbox: list[dict] = Field(default_factory=list)
    cleaned_untrusted_segments: list[Segment] = Field(default_factory=list)


_sessions: dict[str, SessionData] = {}


def get_session(session_id: str) -> SessionData:
    if session_id not in _sessions:
        _sessions[session_id] = SessionData(session_id=session_id)
    return _sessions[session_id]


def reset_session(session_id: str) -> SessionData:
    new_session = SessionData(session_id=session_id)
    _sessions[session_id] = new_session
    return new_session


def update_layers(session_id: str, new_layers: dict[str, bool]) -> LayerSettings:
    session = get_session(session_id)
    current = session.layers.model_dump()
    for k, v in new_layers.items():
        if k in current:
            current[k] = v
        else:
            raise ValueError(f"Unknown layer: {k}")
    session.layers = LayerSettings(**current)
    return session.layers
