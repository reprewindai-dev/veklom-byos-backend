import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('frontend/static/workspace/workspace-enhance.js', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()

# Search for markers like "// ------" or sections that start with page name checks
for i, line in enumerate(lines):
    if '// ------' in line or 'page.includes(' in line or 'hash.includes(' in line:
        print(f"Match on line {i+1}:")
        for j in range(max(0, i-2), min(len(lines), i+15)):
            print(f"  {j+1}: {lines[j]}")
        print("-" * 50)
