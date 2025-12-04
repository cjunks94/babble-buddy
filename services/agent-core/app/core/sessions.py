import uuid
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Session:
    id: str
    app_token_id: int
    messages: list[Message] = field(default_factory=list)
    context: dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, Session] = {}

    def create_session(self, app_token_id: int, context: dict | None = None) -> Session:
        session_id = str(uuid.uuid4())
        session = Session(
            id=session_id,
            app_token_id=app_token_id,
            context=context or {},
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def get_or_create_session(
        self, session_id: str | None, app_token_id: int, context: dict | None = None
    ) -> Session:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            if context:
                session.context.update(context)
            return session
        return self.create_session(app_token_id, context)

    def add_message(self, session_id: str, role: str, content: str) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.messages.append(Message(role=role, content=content))

    def get_messages(self, session_id: str) -> list[Message]:
        session = self._sessions.get(session_id)
        return session.messages if session else []

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False


session_manager = SessionManager()
