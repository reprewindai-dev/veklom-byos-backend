# AGENTS.md — Read This First. Every Agent Must Follow This.

This is the single source of truth for every AI agent working on this repo.
Read completely before touching anything. Violations break the live site.

---

## Live Site

- **URL:** https://veklom.com
- **Workspace:** https://veklom.com/control-plane-next/dashboard/
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

---

## The Correct Workspace — NEVER REPLACE THIS

The true, sovereign workspace is served at `/control-plane-next/` and its assets live in:
```
frontend/sovereign-control-node/
```

**ABSOLUTE RULES — DO NOT VIOLATE**
1. **The only valid frontend directory is `frontend/sovereign-control-node/`.**
2. **ALL OTHER FRONTENDS ARE GARBAGE AND HAVE BEEN DELETED.** Do not look for `frontend/static/workspace` or `frontend/veklom-workspace` or `frontend/static/veklom-control-plane`. If you try to restore them, you will break the live site and anger the user.
3. This is a prebuilt static Next.js export (`out/` directory). Do not attempt to run `npm install` or `npm run build` in this repo. The source code for this frontend is maintained elsewhere.
4. The backend routes `/workspace`, `/login`, and `/signup` all redirect to `/control-plane-next/`.

---

## Add-On Components

| Component | Repo Location | Served At |
|---|---|---|
| Command Center | `frontend/static/command-center/` | `/command-center/` |
| PYO3 IronGrid | `irongrid/dist/` | `/irongrid/` |
| Quantum Terminal | `uacp-quantum-terminal.html` | `/terminal` |
| GPC / UACP V3 | External: `uacpv3.onrender.com` | Iframe inside workspace |

---

## Backend

- **Entry point:** `backend/apps/api/main.py` (FastAPI)
- **Run command:** `uvicorn backend.apps.api.main:app --host 0.0.0.0 --port 8088`
- **All API routes:** prefixed `/api/v1/`
- **Static mounts:** `/control-plane-next`, `/command-center`, `/irongrid`, `/terminal`, `/gpc-engine`

---

## Infrastructure

- **Coolify:** `http://5.78.135.11:8000` (admin panel — do not need to access for deploys)
- **PostgreSQL:** inside `coolify` Docker network, container `llwfyzhnft87bz6brddiax1z`
- **Redis:** inside `coolify` Docker network, container `v8vf3lw73fx9lw9xmbq1tvo5`
- **Traefik proxy:** container `coolify-proxy`, config at `/data/coolify/proxy/`
