#!/bin/bash
echo "=== Assets through public Traefik (Host: veklom.com) ==="
for url in /command-center/assets/index-DCp2a3q7.js \
           /command-center/assets/index-CQ_3ugOq.css \
           /irongrid/assets/index-k10YYEsB.js \
           /irongrid/assets/index-DvEIVjRH.css \
           /workspace/assets/index-EUKZeqk4.js \
           /workspace/assets/index-WqgIFi2m.css \
           /terminal \
           /gpc/ \
           /gpc-engine/; do
  result=$(curl -sk -H "Host: veklom.com" -o /dev/null -w "%{http_code} bytes=%{size_download}" "https://localhost$url")
  printf "%-50s %s\n" "$url" "$result"
done
echo
echo "=== Real public DNS test ==="
for url in / /workspace/ /command-center/ /irongrid/ /terminal /gpc/; do
  result=$(curl -s -o /dev/null -w "%{http_code} bytes=%{size_download}" "https://veklom.com$url")
  printf "%-25s %s\n" "$url" "$result"
done
