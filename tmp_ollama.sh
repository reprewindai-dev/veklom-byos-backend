#!/bin/bash
echo "=== Ollama models ==="
curl -s http://veklom-ollama:11434/api/tags | python3 -c "
import sys,json
d=json.load(sys.stdin)
for m in d.get('models', []):
    print(m['name'], round(m['size']/1e9,1), 'GB')
"

echo ""
echo "=== Test qwen2.5:3b chat ==="
curl -s --max-time 30 http://veklom-ollama:11434/api/chat \
  -d '{"model":"qwen2.5:3b","messages":[{"role":"user","content":"say hi"}],"stream":false}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',{}).get('content','ERROR:'+str(d))[:100])"

echo ""
echo "=== Docker stats for Ollama ==="
docker stats veklom-ollama --no-stream --format "CPU: {{.CPUPerc}}  MEM: {{.MemUsage}}"
