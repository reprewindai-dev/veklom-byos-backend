import os
import re

def scan_backend(path):
    results = {
        "routers_with_mocks": {},
        "core_with_mocks": {},
        "total_mock_mentions": 0
    }
    
    for root, _, files in os.walk(path):
        if "venv" in root or ".git" in root or "__pycache__" in root or "tests" in root:
            continue
            
        for file in files:
            if not file.endswith(".py"):
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                try:
                    content = f.read()
                except UnicodeDecodeError:
                    continue
            
            lines = content.split('\n')
            mock_lines = []
            
            for i, line in enumerate(lines):
                if re.search(r'\b(mock|fake|dummy|hardcoded)\b', line, re.IGNORECASE):
                    mock_lines.append((i+1, line.strip()))
                    results["total_mock_mentions"] += 1
            
            if mock_lines:
                rel_path = os.path.relpath(filepath, path)
                if "routers" in rel_path:
                    results["routers_with_mocks"][rel_path] = mock_lines
                else:
                    results["core_with_mocks"][rel_path] = mock_lines
                    
    return results

veklom = scan_backend("C:\\Users\\antho\\.windsurf\\veklom-byos-backend-2\\backend")
cappo = scan_backend("C:\\Users\\antho\\.windsurf\\cappo-backend")

def format_output(results, name):
    print(f"=== {name} ===")
    print(f"Total mock mentions: {results['total_mock_mentions']}")
    print("\nROUTERS WITH MOCKS:")
    for path, lines in results['routers_with_mocks'].items():
        print(f"  {path} ({len(lines)} mentions)")
        for num, line in lines[:2]: # Show first 2 examples
            print(f"    Line {num}: {line}")
        if len(lines) > 2:
            print("    ...")
            
    print("\nCORE WITH MOCKS:")
    for path, lines in results['core_with_mocks'].items():
        print(f"  {path} ({len(lines)} mentions)")
        for num, line in lines[:2]:
            print(f"    Line {num}: {line}")
        if len(lines) > 2:
            print("    ...")

format_output(veklom, "veklom-byos-backend-2")
print("\n" + "="*50 + "\n")
format_output(cappo, "cappo-backend")
