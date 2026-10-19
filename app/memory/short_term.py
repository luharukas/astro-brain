from collections import defaultdict

MAX_HISTORY_PER_SESSION = 20


class SessionMemory:
    def __init__(self):
        self._sessions: dict[str, list[dict]] = defaultdict(list)

    def add_message(self, session_id: str, role: str, content: str):
        history = self._sessions[session_id]
        history.append({"role": role, "content": content})
        if len(history) > MAX_HISTORY_PER_SESSION:
            self._sessions[session_id] = history[-MAX_HISTORY_PER_SESSION:]

    def get_history(self, session_id: str) -> list[dict]:
        return list(self._sessions[session_id])

    def clear_session(self, session_id: str):
        self._sessions.pop(session_id, None)


session_memory = SessionMemory()
