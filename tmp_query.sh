#!/bin/bash
# Find owner workspace + check env gaps
DB_CONTAINER="llwfyzhnft87bz6brddiax1z"
ENV_FILE="/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env"

echo "=== Owner users ==="
docker exec "$DB_CONTAINER" bash -c '
  PGPASSWORD=$POSTGRES_PASSWORD psql -U $POSTGRES_USER -d $POSTGRES_DB -t -c "
    SELECT id, email, role, workspace_id FROM users
    WHERE role IN ('"'"'OWNER'"'"','"'"'SUPER_ADMIN'"'"') LIMIT 5;
  "
' 2>/dev/null || echo "DB query failed"

echo ""
echo "=== Key env gaps ==="
missing=()
for key in FOUNDER_WORKSPACE_ID GITHUB_CLIENT_ID GITHUB_CLIENT_SECRET OLLAMA_BASE_URL; do
  val=$(grep "^${key}=" "$ENV_FILE" | tail -1 | cut -d= -f2-)
  if [ -z "$val" ] || echo "$val" | grep -qiE "^NEED_|^YOUR_|^CHANGE_|^REPLACE_|^TODO"; then
    echo "  MISSING/PLACEHOLDER: $key = '$val'"
  else
    echo "  OK: $key"
  fi
done
