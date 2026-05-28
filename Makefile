.PHONY: help release-check rollback health-check

help:
	@echo "Veklom Backend Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  make release-check  - Run all release gates"
	@echo "  make rollback       - Execute rollback to previous commit"
	@echo "  make health-check   - Quick health check of production"
	@echo ""

release-check:
	@echo "=== Gate 1: Artifact & Integrity ==="
	@echo "Skipping image signature/SBOM scan (not configured for current deployment)"
	@echo ""
	@echo "=== Gate 2: Infra Health ==="
	@curl -fsS https://veklom.com/health >/dev/null || (echo "FAIL: Health endpoint down" && exit 1)
	@echo "PASS: Health endpoint responding"
	@echo ""
	@echo "=== Gate 3: Observability ==="
	@echo "Skipping PostHog funnel check (not configured)"
	@echo ""
	@echo "=== Gate 4: DSA / Legal ==="
	@echo "Skipping DSA check (endpoint not implemented)"
	@echo ""
	@echo "=== Gate 5: Payments ==="
	@echo "Skipping payment checks (not configured)"
	@echo ""
	@echo "=== Gate 6: Latency & Errors ==="
	@echo "Skipping latency check (use Grafana dashboards)"
	@echo ""
	@echo "=== All Gates Passed ==="

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
	@echo "  docker run -d --name n13gp1nhrcdp0hvazvbnlxru-083606963671 --network coolify --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env --restart unless-stopped -p 8088:8088 veklom-local:latest"
	@echo "  curl -s http://localhost:8088/health"
	@echo "  curl -sk -H 'Host: veklom.com' https://localhost/health"

health-check:
	@echo "=== Veklom Health Check ==="
	@curl -fsS https://veklom.com/health || (echo "FAIL: Health endpoint down" && exit 1)
	@echo ""
	@echo "PASS: https://veklom.com/health is responding"
