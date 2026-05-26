#!/bin/bash
set -e

GATEWAY_SECRET=$(openssl rand -hex 32)
echo "Generated gateway secret: $GATEWAY_SECRET"

cat > /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/paid-gateway/.env << ENVEOF
CDP_API_KEY_ID=PLACEHOLDER_CDP_KEY_ID
CDP_API_KEY_SECRET=PLACEHOLDER_CDP_KEY_SECRET
PAY_TO=0xPLACEHOLDER_YOUR_BASE_WALLET_ADDRESS
UPSTREAM_BASE_URL=http://n13gp1nhrcdp0hvazvbnlxru-213557155694:8088
UPSTREAM_GATEWAY_SECRET=$GATEWAY_SECRET
NETWORK=eip155:8453
PORT=3001
NODE_ENV=production
ENVEOF

echo "=== paid-gateway .env created ==="
head -3 /data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/paid-gateway/.env
echo "..."
echo "UPSTREAM_GATEWAY_SECRET=$GATEWAY_SECRET"

# Also update the FastAPI .env with the same gateway secret
FASTAPI_ENV="/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env"
if grep -q "UPSTREAM_GATEWAY_SECRET" "$FASTAPI_ENV"; then
  sed -i "s/^UPSTREAM_GATEWAY_SECRET=.*/UPSTREAM_GATEWAY_SECRET=$GATEWAY_SECRET/" "$FASTAPI_ENV"
else
  echo "UPSTREAM_GATEWAY_SECRET=$GATEWAY_SECRET" >> "$FASTAPI_ENV"
fi
echo "FastAPI .env updated with UPSTREAM_GATEWAY_SECRET"
