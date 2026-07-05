import os
import re

files_to_process = [
    "agents/agent_gemini.py",
    "agents/agent_groq.py",
    "agents/agent_loop.py",
    "agents/veklom-agents/agent_gemini.py",
    "agents/veklom-agents/agent_groq.py",
    "agents/veklom-agents/agent_loop.py",
    "backend/apps/api/routers/playground.py",
    "backend/apps/api/routers/discovery.py",
    "backend/apps/api/routers/vnp_v2.py"
]

def replace_schema_str(match):
    s = match.group(1)
    s = s.replace('"type":"object","properties"', '"type":"object","additionalProperties":false,"strict":true,"properties"')
    return f'"schema": \'{s}\''

for filepath in files_to_process:
    if not os.path.exists(filepath):
        continue
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace inline empty object schemas
    content = content.replace(
        '"parameters": {"type": "object", "properties": {}, "required": []}',
        '"parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False, "strict": True}'
    )

    # Replace multi-line schemas
    content = content.replace(
        '"parameters": {\n                "type": "object",\n                "properties": {',
        '"parameters": {\n                "type": "object",\n                "additionalProperties": False,\n                "strict": True,\n                "properties": {'
    )
    
    # Replace single line schemas that might have spaces
    content = content.replace(
        '{"type": "object", "properties"',
        '{"type": "object", "additionalProperties": False, "strict": True, "properties"'
    )

    # Replace string JSON schemas in playground.py
    content = re.sub(
        r'"schema": \'(.*?)\'',
        replace_schema_str,
        content
    )

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

print("Applied strict schemas.")
