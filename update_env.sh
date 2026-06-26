#!/bin/bash
ENV=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env
sed -i '/^GITHUB_CLIENT_ID=/d' "$ENV"
sed -i '/^GITHUB_CLIENT_SECRET=/d' "$ENV"
sed -i '/^GITHUB_REDIRECT_URI=/d' "$ENV"
sed -i '/^STRIPE_WEBHOOK_SECRET=/d' "$ENV"
printf 'GITHUB_CLIENT_ID=Iv23liPqr3V9FPknhwIn\nGITHUB_CLIENT_SECRET=<NEW_SECRET>\nGITHUB_REDIRECT_URI=https://api.veklom.com/api/v1/auth/github/callback\n' >> "$ENV"
echo "=== Updated env ==="
grep -E 'GITHUB|STRIPE|OPENAI' "$ENV"
