#!/bin/bash
set -e
C=n13gp1nhrcdp0hvazvbnlxru-213557155694
H=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
cd /tmp
rm -rf vf_full && mkdir vf_full
tar -xzf veklom_full_backend.tgz -C vf_full

FILES="backend/apps/api/main.py
backend/apps/api/routers/admin.py
backend/apps/api/routers/agentic_commerce.py
backend/apps/api/routers/ai.py
backend/apps/api/routers/compliance.py
backend/apps/api/routers/discovery.py
backend/apps/api/routers/exec_router.py
backend/apps/api/routers/monitoring.py
backend/apps/api/routers/pipelines.py
backend/apps/api/routers/security.py
backend/core/privacy/__init__.py
backend/core/privacy/pii.py
backend/core/security/middlewares.py
backend/db/models/__init__.py
backend/db/models/agentic_commerce.py"

for f in $FILES; do
  echo "Deploying $f..."
  docker exec $C mkdir -p /app/$(dirname $f)
  mkdir -p $H/$(dirname $f)
  docker cp vf_full/$f $C:/app/$f
  cp vf_full/$f $H/$f
done

echo "Running py_compile check inside container..."
if docker exec -w /app $C python -m py_compile $FILES; then
  echo "COMPILE_OK"
  echo "Restarting container $C..."
  docker restart $C
else
  echo "COMPILE_FAIL"
  exit 1
fi

echo "Verifying health..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8088/health >/dev/null; then
    echo "HEALTHY"
    break
  fi
  sleep 2
done
