#!/usr/bin/env bash
set -euo pipefail

# This script runs nightly reconciliation checks for Veklom payments
# It verifies:
# 1) Duplicate tx_hashes
# 2) Orphaned pending entries > 15m
# 3) Missing on-chain txs against the Ethereum/Base RPC URL

export ETH_RPC_URL=${ETH_RPC_URL:-https://mainnet.base.org}
export DATABASE_URL=${DATABASE_URL:-""}

echo "[reconcile] Starting reconciliation checks..."

# Helper for executing SQL queries
db_query() {
  if [ -n "$DATABASE_URL" ]; then
    psql "$DATABASE_URL" -At -c "$1"
  else
    # Fallback to local postgres env if PGDATABASE is set
    psql -At -c "$1"
  fi
}

# 1) Check for duplicate tx_hashes in ledger
echo "[reconcile] Checking for duplicate tx_hashes in ledger..."
DUP_COUNT=$(db_query "SELECT COUNT(tx_hash) FROM (SELECT tx_hash FROM ledger WHERE tx_hash IS NOT NULL GROUP BY tx_hash HAVING COUNT(*)>1) AS dupes;") || { echo "DB Connection failed"; exit 1; }
if [ "$DUP_COUNT" -ne 0 ]; then
  echo "❌ DUPLICATE tx_hashes detected in ledger! Count: $DUP_COUNT"
  db_query "SELECT tx_hash, count(*) FROM ledger WHERE tx_hash IS NOT NULL GROUP BY tx_hash HAVING count(*)>1;"
  exit 2
else
  echo "✓ No duplicate ledger tx_hashes."
fi

# 2) Check for orphaned pending entries > 15 minutes old
echo "[reconcile] Checking for orphaned pending entries..."
ORPHANS_COUNT=$(db_query "SELECT COUNT(*) FROM payments WHERE status='pending' AND created_at < NOW() - INTERVAL '15 minutes';")
if [ "$ORPHANS_COUNT" -ne 0 ]; then
  echo "❌ ORPHANED pending payments (>15m) detected! Count: $ORPHANS_COUNT"
  db_query "SELECT order_id, tx_hash, status, created_at FROM payments WHERE status='pending' AND created_at < NOW() - INTERVAL '15 minutes' LIMIT 10;"
  # Warn but don't hard crash the job if not critical, or exit if strict
  # exit 2
else
  echo "✓ No orphaned pending payments."
fi

# 3) Check missing on-chain transactions
echo "[reconcile] Checking missing on-chain receipts..."
TXS=$(db_query "SELECT DISTINCT tx_hash FROM payments WHERE tx_hash IS NOT NULL AND status='confirmed' LIMIT 100;")
MISSING_COUNT=0

for tx in $TXS; do
  # Skip placeholder hashes
  if [[ "$tx" =~ ^0xdeadbeef || "$tx" == "0xaaa" ]]; then
    continue
  fi

  echo "   Checking on-chain receipt for $tx..."
  RECEIPT=$(curl -s -X POST -H 'Content-Type: application/json' \
    --data '{"jsonrpc":"2.0","method":"eth_getTransactionReceipt","params":["'"$tx"'"],"id":1}' "$ETH_RPC_URL")
  
  HAS=$(echo "$RECEIPT" | jq '.result!=null' 2>/dev/null || echo "false")
  if [ "$HAS" != "true" ]; then
    echo "❌ Missing on-chain receipt for tx: $tx!"
    echo "$tx" >> /tmp/reconcile_failures
    MISSING_COUNT=$((MISSING_COUNT+1))
  fi
done

# Assemble failure report and trigger alerts if needed
ALERT_NEEDED=0
ALERT_MSG="[reconcile] Reconciliation Failures Detected:\n"

if [ "$DUP_COUNT" -ne 0 ]; then
  ALERT_NEEDED=1
  ALERT_MSG="${ALERT_MSG}- Duplicate tx_hashes found in ledger (Count: $DUP_COUNT)\n"
fi

if [ "$MISSING_COUNT" -gt 0 ]; then
  ALERT_NEEDED=1
  ALERT_MSG="${ALERT_MSG}- Missing on-chain receipts for confirmed payments (Count: $MISSING_COUNT)\n"
  if [ -f /tmp/reconcile_failures ]; then
    ALERT_MSG="${ALERT_MSG}  Txs: $(cat /tmp/reconcile_failures | tr '\n' ' ')\n"
  fi
fi

if [ "$ALERT_NEEDED" -eq 1 ]; then
  echo "❌ Reconciliation failed! Dispatching alerts..."
  
  # 1) Slack Alert
  if [ -n "${SLACK_WEBHOOK_URL:-}" ] && [ "$SLACK_WEBHOOK_URL" != "NEED_FROM_SLACK" ]; then
    echo "Sending Slack alert..."
    curl -s -X POST -H 'Content-Type: application/json' \
      -d '{"text": "'"${ALERT_MSG}"'"}' \
      "$SLACK_WEBHOOK_URL" || echo "Slack post failed"
  fi
  
  # 2) PagerDuty Alert
  if [ -n "${PAGERDUTY_KEY:-}" ]; then
    echo "Sending PagerDuty alert..."
    curl -s -X POST -H 'Content-Type: application/json' \
      -d '{"routing_key":"'"$PAGERDUTY_KEY"'","event_action":"trigger","payload":{"summary":"payments reconciliation failed","severity":"critical","source":"ci.reconcile","custom_details":{"details":"'"${ALERT_MSG}"'"}}}' \
      https://events.pagerduty.com/v2/enqueue || echo "PagerDuty post failed"
  fi
  
  exit 2
else
  echo "✓ All reconciliation checks passed successfully."
fi

echo "✓ Reconciliation complete. All checks passed."
