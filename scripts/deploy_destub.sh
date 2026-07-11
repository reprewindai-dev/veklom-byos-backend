#!/usr/bin/env bash
# Safe docker-cp deploy for the de-stub change set (PII engine, security/stats,
# explain/*, duplicate-route removals). Compile-gated; only restarts on success.
set -euo pipefail

CONTAINER=n13gp1nhrcdp0hvazvbnlxru-213557155694
HOSTDIR=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
FILES="backend/core/privacy/pii.py \
backend/core/privacy/__init__.py \
backend/apps/api/routers/compliance.py \
backend/apps/api/routers/security.py \
backend/apps/api/routers/monitoring.py \
backend/apps/api/routers/ai.py \
backend/apps/api/routers/admin.py"

cd /tmp
rm -rf vd && mkdir -p vd
tar -xzf /tmp/veklom_destub.tgz -C vd

echo "== copying files into container + host =="
for f in $FILES; do
  docker exec "$CONTAINER" mkdir -p "/app/$(dirname "$f")"
  docker cp "vd/$f" "$CONTAINER:/app/$f"
  mkdir -p "$HOSTDIR/$(dirname "$f")"
  cp "vd/$f" "$HOSTDIR/$f"
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
  if curl -sf http://localhost:80/health >/dev/null; then echo "HEALTHY"; break; fi
  sleep 2
done
echo "DONE"
