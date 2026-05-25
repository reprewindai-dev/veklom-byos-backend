#!/bin/bash
echo "=== veklom.yaml on disk ==="
cat /data/coolify/proxy/dynamic/veklom.yaml
echo
echo "=== Wait 4s for Traefik reload ==="
sleep 4
echo
echo "=== External (through Traefik) ==="
for url in / /health /workspace/ /command-center/ /irongrid/ /terminal /gpc/ /gpc-engine/; do
  code=$(curl -sk -H "Host: veklom.com" -o /dev/null -w "%{http_code}" "https://localhost$url")
  printf "%-25s %s\n" "$url" "$code"
done
