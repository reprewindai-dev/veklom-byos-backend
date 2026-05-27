import re
import glob
import sys

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("Searching for patterns in frontend/static/workspace/ ...")
    patterns = [
        r'sys/health',
        r'sys/gpu',
        r'copilot/registry',
        r'copilot/recent-decisions',
        r'recent-decisions',
        r'gpu',
        r'sys'
    ]
    
    for path in glob.glob('frontend/static/workspace/**/*.js', recursive=True):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        for p in patterns:
            if re.search(p, content):
                print(f"Found {p} in {path}")
                # Print lines containing the pattern
                lines = content.splitlines()
                for i, line in enumerate(lines):
                    if re.search(p, line):
                        print(f"  Line {i+1}: {line.strip()}")

if __name__ == '__main__':
    main()
