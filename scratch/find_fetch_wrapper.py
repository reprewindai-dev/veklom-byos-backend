with open('frontend/static/workspace/workspace-enhance.js', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines()
for i, line in enumerate(lines):
    if 'fetch(' in line:
        print(f"Match on line {i+1}:")
        for j in range(max(0, i-5), min(len(lines), i+15)):
            print(f"  {j+1}: {lines[j]}")
        print("-" * 50)
