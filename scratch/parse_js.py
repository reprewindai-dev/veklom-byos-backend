import re

def main():
    with open('frontend/static/workspace/workspace-enhance.js', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Let's search for fetch calls and see their context
    print("=== Fetch calls ===")
    matches = re.finditer(r'fetch\(\s*[`\'"](.*?)[`\'"]', content)
    for m in matches:
        print(m.group(0))
        
    print("\n=== All base paths and endpoints ===")
    # Let's print all instances of ${base}
    base_matches = re.findall(r'\$\{base\}[^`\s]+', content)
    for bm in sorted(set(base_matches)):
        print(bm)

if __name__ == '__main__':
    main()
