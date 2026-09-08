import re

with open('backend/tests/test_auth_vlink_assertion.py', 'r') as f:
    content = f.read()

new_session = '''class _Session:
    def __init__(self, user, keys=None, bindings=None):
        self.user = user
        self.keys = list(keys or [])
        self.bindings = list(bindings) if bindings is not None else None

    async def execute(self, statement):
        from backend.db.models.vlink_binding import VLinkBinding
        import json
        statement_text = str(statement)
        if "vlink_bindings" in statement_text:
            if self.bindings is not None:
                return _ScalarResult(self.bindings)
            bindings = []
            for k in self.keys:
                scopes = json.loads(k.scopes)
                vlink_id = None
                conn_ref = None
                for s in scopes:
                    if s.startswith("vlink:id:"):
                        vlink_id = s.split(":")[-1]
                    elif s.startswith("vlink:conn:"):
                        conn_ref = s.split(":")[-1]
                if vlink_id:
                    bindings.append(VLinkBinding(
                        id=f"binding-{k.id}",
                        vlink_id=vlink_id,
                        api_key_id=k.id,
                        workspace_id=k.workspace_id,
                        connection_ref=conn_ref,
                        is_active=k.is_active
                    ))
            return _ScalarResult(bindings)
        if "api_keys" in statement_text:
            return _ScalarResult(self.keys)
        if "users" in statement_text:
            return _ScalarResult([self.user] if self.user is not None else [])
        raise AssertionError(f"unexpected query: {statement_text}")

    def add(self, obj):
        if type(obj).__name__ == "APIKey":
            if obj.id is None:
                obj.id = f"key-{len(self.keys) + 1}"
            if obj.is_active is None:
                obj.is_active = True
            self.keys.append(obj)
        elif type(obj).__name__ == "VLinkBinding":
            if self.bindings is None:
                self.bindings = []
            if obj.id is None:
                obj.id = f"binding-{len(self.bindings) + 1}"
            if obj.is_active is None:
                obj.is_active = True
            self.bindings.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        return None'''

start_idx = content.find('class _Session:')
if start_idx != -1:
    end_idx = content.find('def _user', start_idx)
    content = content[:start_idx] + new_session + '\n\n' + content[end_idx:]

with open('backend/tests/test_auth_vlink_assertion.py', 'w') as f:
    f.write(content)

print("Replaced _Session dynamically")
