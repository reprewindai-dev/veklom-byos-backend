#!/bin/bash
curl -s http://localhost:8080/api/http/routers > /tmp/r.json
python3 << 'PYEOF'
import json
d = json.load(open("/tmp/r.json"))
print("Total routers:", len(d))
print()
for r in d:
    name = r.get("name", "?")
    status = r.get("status", "?")
    rule = r.get("rule", "")[:100]
    if "veklom" in (name + rule).lower() or status != "enabled":
        print(f"{status:10} {name:50} {rule}")
PYEOF
