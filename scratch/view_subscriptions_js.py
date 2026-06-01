content = open("frontend/static/control-plane-next/_next/static/chunks/app/subscriptions/page-19ca5687c3928477.js", "r", encoding="utf-8").read()
print("JS Length:", len(content))
# print snippets containing current or plan or tier
import re
for m in re.finditer(r"(.{0,100}(current|plan|tier).{0,100})", content):
    val = m.group(0).strip()
    if len(val) > 200: val = val[:200] + "..."
    print("MATCH:", val)
