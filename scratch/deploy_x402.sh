#!/bin/bash
set -e

APP_DIR="/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru"
CONTAINER="n13gp1nhrcdp0hvazvbnlxru-213557155694"

echo "== copying backend .py into container + host =="
for f in \
  backend/core/middleware/x402.py \
  backend/apps/api/routers/x402.py \
  backend/apps/api/routers/discovery.py \
  backend/apps/api/routers/agentic_commerce.py
do
  echo "  cp $f"
  # Copy to host source
  cp "/tmp/veklom_deploy_work/$f" "$APP_DIR/$f"
  # Copy to live container
  docker cp "/tmp/veklom_deploy_work/$f" "$CONTAINER:/app/$f"
done

echo "== in-container compile gate =="
docker exec $CONTAINER python -m py_compile \
  backend/core/middleware/x402.py \
  backend/apps/api/routers/x402.py \
  backend/apps/api/routers/discovery.py \
  backend/apps/api/routers/agentic_commerce.py
echo "PYCOMPILE_OK"

echo "== restarting container =="
docker restart $CONTAINER
echo "RESTARTED"

echo "== waiting for health =="
for i in {1..20}; do
  if curl -s http://localhost:80/health | grep -q '"status":"healthy"'; then
    echo "HEALTH_OK after $i tries"
    curl -s http://localhost:80/health
    echo ""
    exit 0
  fi
  sleep 2
done

echo "HEALTH_FAIL"
exit 1
