"""Session management for governed agent connections."""

import uuid

class CAPISession:
    def __init__(self, agent_id: str):
        self.session_id = f"cap_{uuid.uuid4().hex[:12]}"
        self.agent_id = agent_id
        self.active_intents = []

    def add_intent(self, intent_token: str):
        self.active_intents.append(intent_token)
