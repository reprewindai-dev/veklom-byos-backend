import re

with open("backend/core/services/autonomous_worker.py", "r") as f:
    content = f.read()

# Replace sleep(0.25) with a tiny sleep to allow context switching but drastically speed up execution
content = re.sub(r'await asyncio\.sleep\(0\.25\)', 'await asyncio.sleep(0.01)', content)

with open("backend/core/services/autonomous_worker.py", "w") as f:
    f.write(content)
