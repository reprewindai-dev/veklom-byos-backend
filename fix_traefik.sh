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
          - url: "http://n13gp1nhrcdp0hvazvbnlxru-213557155694:80"
EOF
sleep 3
curl -s http://localhost:80/health
