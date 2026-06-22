import re

with open("backend/core/services/autonomous_worker.py", "r") as f:
    content = f.read()

# Remove CREATE TABLE from _pgl_register_node
content = re.sub(
    r'await db\.execute\(sql_text\(\s*"""\s*CREATE TABLE IF NOT EXISTS pipeline_governance_ledger.*?"""\s*\)\)',
    '',
    content,
    flags=re.DOTALL
)

# Remove CREATE TABLE from _pgl_lineage_anchor_node
content = re.sub(
    r'await db\.execute\(sql_text\(\s*"""\s*CREATE TABLE IF NOT EXISTS pipeline_lineage_anchors.*?"""\s*\)\)',
    '',
    content,
    flags=re.DOTALL
)

with open("backend/core/services/autonomous_worker.py", "w") as f:
    f.write(content)
