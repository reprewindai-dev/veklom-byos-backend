#!/bin/bash
set -e

echo "Registering Workloads with SPIRE Server..."

# 1. Register the SPIRE Agent node (so it can attest workloads)
docker exec veklom-spire-server bin/spire-server entry create \
    -spiffeID spiffe://veklom.io/ns/infrastructure/sa/agent \
    -selector docker:label:com.docker.compose.service:spire-agent \
    -node

# 2. Register the FastAPI Backend workload
# We attest it based on its container name or compose service label
docker exec veklom-spire-server bin/spire-server entry create \
    -spiffeID spiffe://veklom.io/ns/backend/sa/api \
    -parentID spiffe://veklom.io/ns/infrastructure/sa/agent \
    -selector docker:label:com.docker.compose.service:api

# 3. Register the Celery Worker workload
docker exec veklom-spire-server bin/spire-server entry create \
    -spiffeID spiffe://veklom.io/ns/backend/sa/worker \
    -parentID spiffe://veklom.io/ns/infrastructure/sa/agent \
    -selector docker:label:com.docker.compose.service:celery-worker

echo "Workload registration complete."
docker exec veklom-spire-server bin/spire-server entry show
