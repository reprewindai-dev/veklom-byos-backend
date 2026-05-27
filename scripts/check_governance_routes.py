import sys, json
d = json.load(sys.stdin)
all_paths = sorted(d['paths'].keys())
# governance routes
gov = [p for p in all_paths if 'governance' in p or 'zeno' in p or 'gladiator' in p]
print(f'=== Governance/Zeno/Gladiator routes: {len(gov)} ===')
for p in gov:
    print(p)

# also check security routes
sec = [p for p in all_paths if 'security' in p]
print(f'\n=== Security routes: {len(sec)} ===')
for p in sec:
    print(p)

print(f'\nTotal API routes: {len(all_paths)}')
