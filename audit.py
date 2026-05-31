import os
import re

src_dir = r"C:\Users\antho\.windsurf\veklom-byos-backend-1\frontend\veklom-workspace\src"
target_patterns = [r"setTimeout", r"(?i)mock", r"(?i)fake", r"TODO"]

print("Starting audit for mock patterns...")
for root, _, files in os.walk(src_dir):
    for file in files:
        if file.endswith((".ts", ".tsx")):
            path = os.path.join(root, file)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
                for pattern in target_patterns:
                    matches = re.finditer(pattern, content)
                    for match in matches:
                        # get snippet around match
                        start = max(0, match.start() - 30)
                        end = min(len(content), match.end() + 30)
                        print(f"[{file}] Found '{match.group()}' -> {content[start:end].replace(chr(10), ' ')}")
