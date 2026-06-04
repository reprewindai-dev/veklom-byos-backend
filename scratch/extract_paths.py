import re

def main():
    try:
        with open('frontend/static/workspace/assets/index-EUKZeqk4.js', 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find string literals that look like API paths: "/api/v1/..."
        # In minified JS, they might be in quotes.
        paths = re.findall(r'"(/api/v1/[a-zA-Z0-9/_?-]+)"', content)
        # Also find ones that don't have /api/v1/ just in case it uses a base URL
        short_paths = re.findall(r'"(/[a-zA-Z0-9_-]+/[a-zA-Z0-9/_?-]+)"', content)
        
        all_paths = set(paths + short_paths)
        
        with open('api_routes_utf8.txt', 'w', encoding='utf-8') as out:
            out.write('\n'.join(sorted(all_paths)))
            
        print(f"Extracted {len(all_paths)} paths.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main()
