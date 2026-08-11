set -e
APP=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
PUBLIC_SERVICE=n13gp1nhrcdp0hvazvbnlxru-141959863314
HELPER_CONTAINER=n13gp1nhrcdp0hvazvbnlxru-213557155694
ENVFILE=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env

cd $APP
git fetch origin main
git checkout main
git pull origin main
SHA=$(git rev-parse HEAD)
IMAGE_TAG="${SHA:0:7}"
IMAGE=veklom-local:${IMAGE_TAG}
COOLIFY_IMAGE=n13gp1nhrcdp0hvazvbnlxru:${IMAGE_TAG}

echo "--- Building image ---"
docker build -t "$IMAGE" -t "$COOLIFY_IMAGE" .

echo "--- Running Alembic migrations ---"
docker run --rm \
  --network coolify \
  --env-file "$ENVFILE" \
  -e PYTHONPATH=/app \
  -w /app \
  "$IMAGE" \
  python -m alembic \
    -c backend/db/migrations/alembic.ini \
    upgrade head

echo "--- Recreating Coolify-managed public API container ---"
cp docker-compose.yaml "docker-compose.yaml.pre-${IMAGE_TAG}"
COOLIFY_IMAGE="$COOLIFY_IMAGE" python3 - <<'PY'
import os
import re
from pathlib import Path

path = Path("docker-compose.yaml")
image = os.environ["COOLIFY_IMAGE"]
text = path.read_text()
updated = re.sub(
    r"image:\s*['\"]?n13gp1nhrcdp0hvazvbnlxru:[^'\"\s]+['\"]?",
    f"image: '{image}'",
    text,
    count=1,
)
if updated == text:
    raise SystemExit("Coolify image line not found in docker-compose.yaml")
path.write_text(updated)
PY
docker compose -f docker-compose.yaml up -d --force-recreate --no-deps "$PUBLIC_SERVICE"

echo "--- Recreating internal helper API container ---"
docker stop "$HELPER_CONTAINER" >/dev/null 2>&1 || true
docker rm "$HELPER_CONTAINER" >/dev/null 2>&1 || true
docker run -d \
  --name "$HELPER_CONTAINER" \
  --network coolify \
  --restart unless-stopped \
  --env-file "$ENVFILE" \
  -e VNP_INPROCESS_PROBES_ENABLED=true \
  -e PORT=8088 \
  -e PYTHONPATH=/app \
  -w /app \
  --label veklom.workload=backend-api \
  "$COOLIFY_IMAGE" \
  uvicorn backend.apps.api.main:app --host 0.0.0.0 --port 8088 >/dev/null

echo "BYOS deployment complete"
