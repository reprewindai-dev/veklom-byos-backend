import sys
sys.stdout.reconfigure(encoding='utf-8')

def main():
    with open('frontend/static/workspace/workspace-enhance.js', 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.splitlines()
    
    sections = [
        "USER DROPDOWN",
        "OVERVIEW",
        "PLAYGROUND",
        "MARKETPLACE",
        "MODELS",
        "PIPELINES",
        "DEPLOYMENTS",
        "VAULT",
        "COMPLIANCE",
        "MONITORING",
        "BILLING",
        "TEAM",
        "SETTINGS"
    ]
    
    for sec in sections:
        marker = f"// ------ {sec} ------"
        start = -1
        for i, line in enumerate(lines):
            if marker in line:
                start = i
                break
        if start != -1:
            print(f"=== SECTION: {sec} (starts at line {start+1}) ===")
            # Print up to 100 lines or until the next section
            end = min(len(lines), start + 100)
            for j in range(start, end):
                # if another marker starts, break
                if j > start and '// ------' in lines[j] and any(s in lines[j] for s in sections):
                    break
                print(f"  {j+1}: {lines[j]}")
            print("-" * 60)
        else:
            print(f"=== SECTION: {sec} (NOT FOUND) ===")

if __name__ == '__main__':
    main()
