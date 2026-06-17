# Deploy Runbook

## Standard Deploy (after git push)
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

# Verify
curl -s http://localhost:8088/health
```

## If Site Shows "No Server Available"
```bash
cat > /data/coolify/proxy/dynamic/veklom.yaml << 'EOF'
http:
  routers:
    veklom:
      entryPoints: [http, https]
      rule: "Host(`veklom.com`) || Host(`www.veklom.com`)"
      service: veklom
      tls:
        certResolver: letsencrypt
  services:
    veklom:
      loadBalancer:
        servers:
          - url: "http://n13gp1nhrcdp0hvazvbnlxru-213557155694:8088"
EOF
sleep 3 && curl -sk -H "Host: veklom.com" https://localhost/health
```

## Infrastructure
- PostgreSQL: container llwfyzhnft87bz6brddiax1z
- Redis: container v8vf3lw73fx9lw9xmbq1tvo5
- Both inside 'coolify' Docker network
- Env file: /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env
