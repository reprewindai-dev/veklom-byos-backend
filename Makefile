.PHONY: help release-check rollback health-check smoke-x402 reconcile

help:
	@echo "Veklom Backend Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make release-check  - Run all release gates"
	@echo "  make rollback       - Execute rollback to previous commit"
	@echo "  make health-check   - Quick health check of production"
	@echo "  make smoke-x402     - Execute E2E wallet->relayer->webhook->ledger smoke test"
	@echo "  make reconcile      - Run payments & ledger reconciliation check"
	@echo ""


release-check:
	@echo "=== Gate 1: Python compilation ==="
	python -m compileall -q backend
	@echo "PASS: Python compilation"
	@echo "=== Gate 2: Alembic single head ==="
	@heads=$$(python -m alembic -c backend/db/migrations/alembic.ini heads | grep -c '(head)'); \
	if [ "$$heads" -ne 1 ]; then echo "FAIL: expected one Alembic head, found $$heads"; exit 1; fi
	@echo "PASS: one Alembic head"
	@echo "=== Gate 3: Tests ==="
	python -m pytest backend/tests -q
	@echo "=== Gate 4: Lint ==="
	python -m ruff check backend
	@echo "=== Gate 5: Readiness ==="
	curl -fsS https://api.veklom.com/ready >/dev/null
	@echo "PASS: readiness endpoint responding"
	@echo "=== All release gates passed ==="

rollback:
	@echo "=== Veklom Rollback ==="
	@echo "Finding previous commit..."
	@echo "Run these commands manually:"
	@echo "  ssh -i ~/.ssh/veklom-deploy root@5.78.135.11"
	@echo "  cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru"
	@echo "  git log --oneline -5"
	@echo "  git checkout <previous_commit_sha>"
	@echo "  docker build -t veklom-local:latest ."
	@echo "  docker stop n13gp1nhrcdp0hvazvbnlxru-083606963671 || true"
	@echo "  docker rm n13gp1nhrcdp0hvazvbnlxru-083606963671 || true"
	@echo "  docker run -d --name n13gp1nhrcdp0hvazvbnlxru-083606963671 --network coolify --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env --restart unless-stopped -p 80:80 veklom-local:latest"
	@echo "  curl -s http://localhost:80/health"
	@echo "  curl -sk -H 'Host: veklom.com' https://localhost/health"

health-check:
	@echo "=== Veklom Health Check ==="
	@curl -fsS https://api.veklom.com/ready || (echo "FAIL: Readiness endpoint down" && exit 1)
	@echo ""
	@echo "PASS: https://api.veklom.com/ready is responding"

smoke-x402:
	@echo "=== E2E Wallet->Relayer->Webhook->Ledger Smoke Test ==="
	python scripts/smoke_x402.py

reconcile:
	@echo "=== Running Payments & Ledger Reconciliation ==="
	chmod +x ./scripts/reconcile.sh
	./scripts/reconcile.sh

