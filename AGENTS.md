# AGENTS.md — Read This First. Every Agent Must Follow This.

This is the single source of truth for every AI agent working on this repo.
Read completely before touching anything. Violations break the live site.

---

## Live Site

- **URL:** https://veklom.com
- **Workspace:** https://veklom.com/workspace/
- **Server:** Hetzner VPS `5.78.135.11`
- **Internal port:** `8088`
- **Proxy:** Cloudflare (443 → 8088 via Traefik on the server)

---

## SSH Into the Server

```bash
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11
```

The key `veklom-deploy` lives at `C:\Users\antho\.ssh\veklom-deploy` on the local machine.
No password. Key-only auth. This always works.

---

## Application on the Server

| Item | Value |
|---|---|
| Source directory | `/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/` |
| Container name | `n13gp1nhrcdp0hvazvbnlxru-213557155694` |
| Docker image | `veklom-local:latest` |
| Docker network | `coolify` |
| Env file | `/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env` |
| Traefik config | `/data/coolify/proxy/dynamic/veklom.yaml` |

---

## How to Deploy After Any Code Change

**Step 1 — Push to GitHub:**
```bash
git add -A
git commit -m "your message"
git push origin main
```

**Step 2 — SSH and rebuild on the server:**
```bash
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11

cd /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru
git pull origin main
docker build -t veklom-local:latest .
docker stop n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
docker rm n13gp1nhrcdp0hvazvbnlxru-213557155694 || true
docker run -d \
  --name n13gp1nhrcdp0hvazvbnlxru-213557155694 \
  --network coolify \
  --env-file /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env \
  --restart unless-stopped \
  -p 8088:8088 \
  veklom-local:latest
```

**Step 3 — Verify:**
```bash
curl -s http://localhost:8088/health
curl -sk https://localhost/health -H "Host: veklom.com"
```

Both should return `{"status":"healthy",...}`.

**GitHub Actions** (`.github/workflows/deploy.yml`) automates Steps 2-3 on every push
to `main` once `HETZNER_SSH_KEY` is added as a GitHub repo secret.

---

## If the Site Shows "No Server Available"

Traefik lost its routing config. Fix it:

```bash
ssh -i ~/.ssh/veklom-deploy root@5.78.135.11

# Check the Traefik routing file exists:
cat /data/coolify/proxy/dynamic/veklom.yaml

# If missing or wrong, recreate it:
cat > /data/coolify/proxy/dynamic/veklom.yaml << 'EOF'
http:
  routers:
    veklom:
      entryPoints:
        - http
        - https
      rule: "Host(`veklom.com`) || Host(`www.veklom.com`) || Host(`app.veklom.com`)"
      service: veklom
      tls:
        certResolver: letsencrypt
  services:
    veklom:
      loadBalancer:
        servers:
          - url: "http://n13gp1nhrcdp0hvazvbnlxru-213557155694:8088"
EOF

# Traefik auto-reloads. Verify:
sleep 3 && curl -sk -H "Host: veklom.com" https://localhost/health
```

## The Correct Workspace — NEVER REPLACE THIS

The workspace at `/workspace/` redirects to the true Next.js control plane served from:
```
frontend/static/veklom-control-plane/
```

This is the **REAL FRONTEND** — a Next.js application built to replace the old legacy Vite app.

**Required source:**
The source code for the frontend is located at `frontend/veklom-workspace/`.

---

## Add-On Components

| Component | Repo Location | Served At |
|---|---|---|
| Command Center | `frontend/static/command-center/` | `/command-center/` |
| PYO3 IronGrid | `irongrid/dist/` | `/irongrid/` |
| Quantum Terminal | `uacp-quantum-terminal.html` | `/terminal` |
| GPC / UACP V3 | External: `uacpv3.onrender.com` | Iframe inside workspace |

---

## ABSOLUTE RULES — DO NOT VIOLATE

1. **NEVER mention or attempt to restore the legacy Vite React app.** It has been completely purged from the repository.
2. **After EVERY git push, you MUST also SSH and rebuild on the server.**
   Git push alone does NOT update the live site unless GitHub Actions runs.
3. **If you manually recreate the Docker container, you MUST also verify
   `/data/coolify/proxy/dynamic/veklom.yaml` still exists with correct config.**
   Without it, Traefik cannot route traffic and the site shows "no server available."
4. **Do not change the container name.** It must stay `n13gp1nhrcdp0hvazvbnlxru-213557155694`.

---

## Backend

- **Entry point:** `backend/apps/api/main.py` (FastAPI)
- **Run command:** `uvicorn backend.apps.api.main:app --host 0.0.0.0 --port 8088`
- **All API routes:** prefixed `/api/v1/`
- **Static mounts:** `/workspace`, `/command-center`, `/irongrid`, `/terminal`, `/gpc-engine`

---

## Infrastructure

- **Coolify:** `http://5.78.135.11:8000` (admin panel — do not need to access for deploys)
- **PostgreSQL:** inside `coolify` Docker network, container `llwfyzhnft87bz6brddiax1z`
- **Redis:** inside `coolify` Docker network, container `v8vf3lw73fx9lw9xmbq1tvo5`
- **Traefik proxy:** container `coolify-proxy`, config at `/data/coolify/proxy/`
