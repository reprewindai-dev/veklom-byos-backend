import re

def main():
    with open('frontend/static/workspace/workspace-enhance.js', 'r', encoding='utf-8') as f:
        content = f.read()
        
    lines = content.splitlines()
    for i, line in enumerate(lines):
        if 'function fetch' in line or 'async' in line and 'fetch' in line:
            print(f"Line {i+1}:")
            for j in range(max(0, i-5), min(len(lines), i+30)):
                print(f"  {j+1}: {lines[j]}")
            print("-" * 40)

if __name__ == '__main__':
    main()
