#!/usr/bin/env bash
# Veklom x402 pay-per-call helper.
#
# Usage:
#   # 1) Probe a paid route to get the price + treasury address:
#   ./pay_x402_flow.sh probe /api/v1/gpc/runs '{"plan_id":"abc"}'
#
#   # 2) After sending USDC on Base to the treasury, run the call with proof:
#   ./pay_x402_flow.sh pay /api/v1/gpc/runs '{"plan_id":"abc"}' 0x<tx_hash>
#
# The agent runtime is responsible for the actual USDC transfer (e.g. via the
# bankr skill). This script handles the 402 probe and the proof-carrying retry.
set -euo pipefail

BASE="${VEKLOM_API_BASE:-https://veklom.com}"
MODE="${1:?mode required: probe|pay}"
ROUTE="${2:?route required, e.g. /api/v1/gpc/runs}"
DATA="${3:-{}}"
TX_HASH="${4:-}"

probe() {
  echo "Probing ${BASE}${ROUTE} ..." >&2
  curl -sS -D - -o /tmp/veklom_body.json -X POST "${BASE}${ROUTE}" \
    -H "Content-Type: application/json" -d "${DATA}" | \
    grep -i -E '^(HTTP/|x-payment-)' || true
  echo "--- body ---" >&2
  cat /tmp/veklom_body.json
  echo
  echo "Send USDC on Base to the X-Payment-Address above for X-Payment-Price-USDC," >&2
  echo "then re-run with: pay ${ROUTE} '${DATA}' 0x<tx_hash>" >&2
}

pay() {
  [ -n "${TX_HASH}" ] || { echo "tx_hash required for pay mode" >&2; exit 1; }
  # Stable idempotency key derived from route+data so retries are not double-charged.
  IDEM="$(printf '%s' "${ROUTE}${DATA}" | sha256sum | cut -c1-32)"
  echo "Submitting paid call with proof ${TX_HASH} (idem ${IDEM}) ..." >&2
  curl -sS -X POST "${BASE}${ROUTE}" \
    -H "Content-Type: application/json" \
    -H "X-Payment-Proof: ${TX_HASH}" \
    -H "Idempotency-Key: ${IDEM}" \
    -d "${DATA}"
  echo
}

case "${MODE}" in
  probe) probe ;;
  pay)   pay ;;
  *) echo "unknown mode: ${MODE} (use probe|pay)" >&2; exit 1 ;;
esac
