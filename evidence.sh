#!/usr/bin/env bash
set -euo pipefail

# ---------- Config (via env) ----------
: "${TARGET_URL:=https://veklom.com}"
: "${POSTHOG_API_KEY:=}"                 # optional
: "${POSTHOG_PROJECT:=}"                 # e.g. 12345
: "${POSTHOG_DISTINCT_ID:=}"             # user id you care about
: "${ETH_RPC_URL:=}"                     # optional: https://...
: "${TX_HASHES:=}"                       # space-separated tx ids: "0xabc 0xdef ..."
: "${OPENSSL_KEY:=private.pem}"          # optional for signing
: "${COSIGN_KEY:=}"                      # optional cosign key path

# ---------- Bootstrap ----------
mkdir -p evidence
if ! command -v node >/dev/null 2>&1; then echo "Please install Node (>=18)"; exit 1; fi
if ! command -v npx  >/dev/null 2>&1; then echo "Please install npm/npx"; exit 1; fi

if [ ! -f package.json ]; then
  npm init -y >/dev/null
fi
npm i -D @playwright/test >/dev/null
npx playwright install >/dev/null

# Write a minimal Playwright spec
cat > tests/evidence.spec.js <<'JS'
const { test } = require('@playwright/test');
const fs = require('fs');
test('collect evidence', async ({ browser }) => {
  const context = await browser.newContext({ recordHar: { path: 'evidence/network.har' } });
  const page = await context.newPage();
  const logs = [];
  page.on('console', m => logs.push(`${m.type()}: ${m.text()}`));

  await page.goto(process.env.TARGET_URL || 'https://veklom.com', { waitUntil: 'networkidle' });
  await page.screenshot({ path: 'evidence/home.png', fullPage: true });

  fs.writeFileSync('evidence/console.log', logs.join('\n') || '');
  await context.close();
});
JS

# ---------- Run Playwright ----------
echo "Running Playwright against ${TARGET_URL}..."
npx playwright test tests/evidence.spec.js --project=chromium --reporter=list || true

# ---------- Pull PostHog (optional) ----------
if [ -n "${POSTHOG_API_KEY}" ] && [ -n "${POSTHOG_PROJECT}" ] && [ -n "${POSTHOG_DISTINCT_ID}" ]; then
  echo "Fetching PostHog events..."
  curl -s -H "Authorization: Bearer ${POSTHOG_API_KEY}" \
    "https://app.posthog.com/api/projects/${POSTHOG_PROJECT}/events?limit=500&distinct_id=${POSTHOG_DISTINCT_ID}" \
    -o evidence/posthog_events.json || echo '{}' > evidence/posthog_events.json
else
  echo '{}' > evidence/posthog_events.json
fi

# ---------- On-chain receipts (optional) ----------
if [ -n "${ETH_RPC_URL}" ] && [ -n "${TX_HASHES}" ]; then
  for TX in ${TX_HASHES}; do
    echo "Fetching receipt for ${TX}..."
    curl -s -X POST -H "Content-Type: application/json" \
      --data '{"jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":["'"${TX}"'"],"id":1}' \
      "${ETH_RPC_URL}" -o "evidence/tx_receipt_${TX:0:10}.json"
  done
fi

# ---------- Attestation ----------
TS=$(date -u +%Y-%m-%dT%H:%M:%SZ)
GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
NODE_VER=$(node -v)
PW_VER=$(npx playwright --version 2>/dev/null || echo "unknown")
CI_RUN_ID="${CI_RUN_ID:-local}"

node -e "const fs=require('fs');
const att={
  timestamp:'${TS}',
  git_commit:'${GIT_COMMIT}',
  ci_run:'${CI_RUN_ID}',
  node:'${NODE_VER}',
  playwright:'${PW_VER}',
  target_url: process.env.TARGET_URL || '${TARGET_URL}',
  artifacts:['network.har','home.png','console.log','posthog_events.json']
};
fs.writeFileSync('evidence/attestation.json', JSON.stringify(att,null,2));"

# ---------- Bundle + checksum ----------
TAG=$(date -u +%Y%m%dT%H%M%SZ)
ZIP="evidence-${TAG}.zip"
echo "Bundling ${ZIP}..."
zip -qr "${ZIP}" evidence
sha256sum "${ZIP}" | awk '{print $1 "  " $2}' > "${ZIP}.sha256"

# ---------- Sign (OpenSSL or Cosign, optional) ----------
if [ -f "${OPENSSL_KEY}" ]; then
  echo "Signing with OpenSSL key: ${OPENSSL_KEY}"
  openssl dgst -sha256 -sign "${OPENSSL_KEY}" -out "${ZIP}.sig" "${ZIP}" || true
fi
if [ -n "${COSIGN_KEY}" ]; then
  echo "Signing with Cosign key: ${COSIGN_KEY}"
  cosign sign-blob --key "${COSIGN_KEY}" --output-signature "${ZIP}.cosign" "${ZIP}" || true
fi

# ---------- Done ----------
echo
echo "Artifacts:"
ls -lh "${ZIP}"* evidence/ | sed 's/^/  /'
echo
echo "Verify checksum:   sha256sum -c ${ZIP}.sha256"
echo "Verify OpenSSL:    openssl dgst -sha256 -verify public.pem -signature ${ZIP}.sig ${ZIP}   (if used)"
echo "Verify Cosign:     cosign verify-blob --key cosign.pub --signature ${ZIP}.cosign ${ZIP}   (if used)"
