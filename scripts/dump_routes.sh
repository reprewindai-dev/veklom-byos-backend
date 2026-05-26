#!/bin/bash
# Dumps the live backend's OpenAPI spec into a flat method+path inventory.
# Source of truth: the running container's /openapi.json (no local code parsing).
set -e
OUT=/tmp/veklom_routes.txt
JSON=/tmp/veklom_openapi.json

curl -s http://localhost:8088/openapi.json > "$JSON"
echo "Total bytes: $(wc -c < "$JSON")"

python3 - <<'PYEOF' > "$OUT"
import json
spec = json.load(open("/tmp/veklom_openapi.json"))
paths = spec.get("paths", {})
rows = []
for path, methods in paths.items():
    for method, op in methods.items():
        if method.lower() not in ("get","post","put","patch","delete"):
            continue
        op_id = op.get("operationId", "")
        tags = ",".join(op.get("tags", []))
        sec = "auth" if op.get("security") else ""
        rows.append((method.upper(), path, tags, sec, op_id))
rows.sort(key=lambda r: (r[1], r[0]))
print(f"{'METHOD':<7} {'PATH':<70} {'TAGS':<25} {'AUTH':<6} OPERATION_ID")
print("-" * 140)
for m, p, t, s, o in rows:
    print(f"{m:<7} {p:<70} {t:<25} {s:<6} {o}")
print()
print(f"TOTAL ROUTES: {len(rows)}")
PYEOF

echo "Written to $OUT"
wc -l "$OUT"
