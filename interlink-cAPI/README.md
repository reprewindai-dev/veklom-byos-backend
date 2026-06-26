# interlink-cAPI

Governed connection layer between agents and API resources.
STANDALONE SERVICE for Veklom Production Architecture.

## Features
- Execution Intent Evaluation (PGL 9-phase gate)
- Signed Evidence Receipts
- Governance Audit Portal
- webcAPI Transport (webMCP Extension)

## Running
```bash
docker build -t interlink-capi .
docker run -p 8089:8089 interlink-capi
```
