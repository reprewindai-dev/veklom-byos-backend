#!/bin/bash
ENV=/data/coolify/applications/n13gp1nhrcdp0hvazvbnlxru/.env

# Fix the missing newline before HOST=0.0.0.0GITHUB... issue
# and deduplicate any double GITHUB lines
# 1. Add a newline at end if missing
sed -i -e '$a\' "$ENV"

# 2. Fix the mangled HOST=0.0.0.0GITHUB line
sed -i 's/HOST=0\.0\.0\.0GITHUB_CLIENT_ID=.*/HOST=0.0.0.0/' "$ENV"

# 3. Remove duplicate GITHUB lines (keep last occurrence by removing all then re-appending)
sed -i '/^GITHUB_CLIENT_ID=/d' "$ENV"
sed -i '/^GITHUB_CLIENT_SECRET=/d' "$ENV"
sed -i '/^GITHUB_REDIRECT_URI=/d' "$ENV"

# 4. Ensure file ends with newline, then append
echo "" >> "$ENV"
echo "GITHUB_CLIENT_ID=Ov23lijPnrtxwjtoP2vk" >> "$ENV"
echo "GITHUB_CLIENT_SECRET=<NEW_SECRET>" >> "$ENV"
echo "GITHUB_REDIRECT_URI=https://api.veklom.com/api/v1/auth/github/callback" >> "$ENV"

# 5. Remove blank lines
sed -i '/^$/d' "$ENV"

echo "=== Final env (GITHUB/STRIPE/OPENAI/HOST lines) ==="
grep -E 'GITHUB|STRIPE|OPENAI|HOST' "$ENV"
