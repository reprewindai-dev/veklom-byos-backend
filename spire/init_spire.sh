#!/bin/bash
set -e

echo "Generating join token for SPIRE Agent..."
# Generate token on server
TOKEN=$(docker exec veklom-spire-server bin/spire-server token generate -spiffeID spiffe://veklom.io/ns/infrastructure/sa/agent -t 3600 | awk '{print $2}')
echo "Token generated: $TOKEN"

echo "Joining SPIRE Agent to Server..."
# Pass token to agent
docker exec veklom-spire-agent bin/spire-agent run -config /opt/spire/conf/agent/agent.conf -joinToken $TOKEN &

echo "SPIRE infrastructure initialized."
