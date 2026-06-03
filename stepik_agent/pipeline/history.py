from models.schemas import SessionMessage


MAX_HISTORY = 40


class MessageHistory:
    """Bounded chat history for the orchestrator."""

    def __init__(self) -> None:
        self._messages: list[SessionMessage] = []

    def add(self, role: str, content: str) -> None:
        self._messages.append(SessionMessage(role=role, content=content))
        if len(self._messages) > MAX_HISTORY:
            self._messages = self._messages[-MAX_HISTORY:]

    def as_openai(self) -> list[dict]:
        return [{"role": m.role, "content": m.content} for m in self._messages]

    def last_user_text(self) -> str | None:
        for msg in reversed(self._messages):
            if msg.role == "user":
                return msg.content
        return None

    def format_for_prompt(self, limit: int = 12) -> str:
        chunk = self._messages[-limit:]
        return "\n".join(f"{m.role}: {m.content}" for m in chunk)
