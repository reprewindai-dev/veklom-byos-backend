import sys, json
d = json.load(sys.stdin)
paths = sorted([p for p in d['paths'].keys() if 'internal/operators' in p])
print(f"=== Internal Operator routes: {len(paths)} ===")
for p in paths:
    print(p)
