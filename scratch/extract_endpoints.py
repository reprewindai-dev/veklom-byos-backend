import re

def main():
    with open('frontend/static/workspace/workspace-enhance.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all base + string templates
    paths = set()
    # Matches `${base}/something`
    for m in re.finditer(r'\$\{base\}(/[^`\'"\s?&}]+)', content):
        paths.add(m.group(1))
    
    # Also find any hardcoded "/api/v1/..." strings
    for m in re.finditer(r'[\'"`](/api/v1/[^\'"`]+)[\'"`]', content):
        paths.add(m.group(1))
        
    print("Found endpoints:")
    for p in sorted(paths):
        print(f"  {p}")

if __name__ == '__main__':
    main()
