import re

with open("backend/core/database/database.py", "r") as f:
    content = f.read()

# Increase pool_size and max_overflow for high concurrency
content = re.sub(
    r'pool_size=20,',
    'pool_size=50,',
    content
)
content = re.sub(
    r'max_overflow=30,',
    'max_overflow=50,',
    content
)

with open("backend/core/database/database.py", "w") as f:
    f.write(content)
