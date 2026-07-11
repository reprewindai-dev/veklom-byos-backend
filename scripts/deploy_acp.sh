#!/usr/bin/env bash
# Safe docker-cp deploy for the agentic-commerce change set.
# Copies changed .py files into the running container AND the host app dir,
# runs an in-container py_compile GATE (only restarts if it passes), then
# verifies health + the new public routes. No git rebuild -> no frontend risk.
set -euo pipefail

CONTAINER=n13gp1nhrcdp0hvazvbnlxru-213557155694
HOSTDIR=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
FILES="backend/apps/api/routers/agentic_commerce.py \
backend/db/models/agentic_commerce.py \
backend/apps/api/main.py \
backend/core/security/middlewares.py \
backend/apps/api/routers/discovery.py \
backend/db/models/__init__.py"

cd /tmp
rm -rf veklom_acp && mkdir -p veklom_acp
tar -xzf /tmp/veklom_acp.tgz -C veklom_acp

echo "== copying files into container + host =="
for f in $FILES; do
  docker exec "$CONTAINER" mkdir -p "/app/$(dirname "$f")"
  docker cp "veklom_acp/$f" "$CONTAINER:/app/$f"
  mkdir -p "$HOSTDIR/$(dirname "$f")"
  cp "veklom_acp/$f" "$HOSTDIR/$f"
  echo "  ok $f"
done

echo "== in-container compile gate =="
if docker exec -w /app "$CONTAINER" python -m py_compile $FILES; then
  echo "COMPILE_OK -> restarting"
  docker restart "$CONTAINER"
else
  echo "COMPILE_FAILED -> NOT restarting (live code unchanged)"
  exit 1
fi

echo "== waiting for health =="
for i in $(seq 1 30); do
  if curl -sf http://localhost:80/health >/dev/null; then echo "healthy"; break; fi
  sleep 2
done

echo "== verify new routes =="
echo "-- agent.json commerce block --"
curl -s http://localhost:80/.well-known/agent.json | grep -o '"commerce"' || echo "MISSING commerce block"
echo "-- product_feed --"
curl -s http://localhost:80/api/v1/agentic_commerce/product_feed | head -c 300
echo
echo "DONE"
