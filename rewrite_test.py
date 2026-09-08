import re

with open('backend/tests/test_auth_vlink_assertion.py', 'r') as f:
    content = f.read()

new_session = '''class _Session:
    def __init__(self, user, keys=None, bindings=None):
        self.user = user
        self.keys = list(keys or [])
        self.bindings = list(bindings or [])

    async def execute(self, statement):
        statement_text = str(statement)
        if "vlink_bindings" in statement_text:
            return _ScalarResult(self.bindings)
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
            if obj.id is None:
                obj.id = f"binding-{len(self.bindings) + 1}"
            if obj.is_active is None: obj.is_active = True`n            self.bindings.append(obj)

    async def flush(self):
        pass

    async def commit(self):
        return None'''

# Replace _Session
start_idx = content.find('class _Session:')
if start_idx != -1:
    end_idx = content.find('def _user', start_idx)
    content = content[:start_idx] + new_session + '\n\n' + content[end_idx:]

with open('backend/tests/test_auth_vlink_assertion.py', 'w') as f:
    f.write(content)

print("Replaced _Session")
