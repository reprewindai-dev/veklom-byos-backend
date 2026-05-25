#!/bin/bash
# Fix .env issues:
# 1. Split merged HOST=0.0.0.0OLLAMA_BASE_URL= line
# 2. Remove trailing empty GITHUB_CLIENT_ID= and GITHUB_CLIENT_SECRET= overrides
# 3. Replace NEED_FROM_GITHUB placeholders with blanks (user must fill manually)
# 4. Add FOUNDER_WORKSPACE_ID placeholder

ENV="/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env"
BAK="${ENV}.bak.$(date +%s)"

cp "$ENV" "$BAK"
echo "Backup at $BAK"

# Fix merged line: HOST=0.0.0.0OLLAMA_BASE_URL=... -> two separate lines
sed -i 's/^HOST=0\.0\.0\.0OLLAMA_BASE_URL=/HOST=0.0.0.0\nOLLAMA_BASE_URL=/' "$ENV"

# Remove trailing blank GITHUB overrides (the empty ones that kill the real values)
sed -i '/^GITHUB_CLIENT_ID=$/d' "$ENV"
sed -i '/^GITHUB_CLIENT_SECRET=$/d' "$ENV"

# Check if FOUNDER_WORKSPACE_ID is set; add placeholder if not
if ! grep -q '^FOUNDER_WORKSPACE_ID=' "$ENV"; then
  echo "" >> "$ENV"
  echo "# Set this to your workspace UUID after first login (SELECT id FROM workspaces LIMIT 1;)" >> "$ENV"
  echo "FOUNDER_WORKSPACE_ID=" >> "$ENV"
fi

echo ""
echo "=== Fixed .env (relevant lines) ==="
grep -n 'OLLAMA_BASE_URL\|GITHUB_CLIENT\|FOUNDER_WORKSPACE\|^HOST=' "$ENV"

echo ""
echo "=== Ollama reachability test ==="
OLLAMA_URL=$(grep '^OLLAMA_BASE_URL=' "$ENV" | head -1 | cut -d= -f2-)
echo "OLLAMA_BASE_URL=$OLLAMA_URL"
curl -s --max-time 3 "${OLLAMA_URL}/api/version" 2>&1 | head -c 100 || echo "(unreachable)"
