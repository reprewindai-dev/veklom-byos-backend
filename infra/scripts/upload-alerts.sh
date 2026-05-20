#!/usr/bin/env bash
# Veklom BYOS Backend — Upload Prometheus alert rules to Grafana Cloud
# Grafana Cloud Canada East (prod-ca-east-0)
# Grafana Instance ID: 1652772
# Grafana URL: https://reprewindaidev.grafana.net
#
# Usage:
#   export GRAFANA_API_TOKEN=your_token
#   bash infra/scripts/upload-alerts.sh
#
# The rules.yml is uploaded as a Mimir ruler namespace named "veklom-backend".
# After upload, rules are visible in Grafana Cloud → Alerting → Alert Rules.

set -euo pipefail

GRAFANA_URL="https://prometheus-prod-32-prod-ca-east-0.grafana.net"
PROM_USER_ID="3229768"
NAMESPACE="veklom-backend"
RULES_FILE="$(dirname "$0")/../alerts/rules.yml"

if [[ -z "${GRAFANA_API_TOKEN:-}" ]]; then
  echo "ERROR: GRAFANA_API_TOKEN is not set."
  echo "  export GRAFANA_API_TOKEN=your_token"
  exit 1
fi

if [[ ! -f "$RULES_FILE" ]]; then
  echo "ERROR: Rules file not found at $RULES_FILE"
  exit 1
fi

echo "→ Uploading alert rules to Grafana Cloud Mimir ruler..."
echo "  URL:       ${GRAFANA_URL}"
echo "  User ID:   ${PROM_USER_ID}"
echo "  Namespace: ${NAMESPACE}"
echo "  File:      ${RULES_FILE}"
echo ""

HTTP_STATUS=$(curl -s -o /tmp/upload_response.txt -w "%{http_code}" \
  -X POST \
  "${GRAFANA_URL}/api/prom/rules/${NAMESPACE}" \
  -H "Content-Type: application/yaml" \
  -u "${PROM_USER_ID}:${GRAFANA_API_TOKEN}" \
  --data-binary @"${RULES_FILE}")

RESPONSE=$(cat /tmp/upload_response.txt)

if [[ "$HTTP_STATUS" == "202" || "$HTTP_STATUS" == "200" ]]; then
  echo "✓ Alert rules uploaded successfully (HTTP ${HTTP_STATUS})"
  echo ""
  echo "View rules at:"
  echo "  https://reprewindaidev.grafana.net/alerting/list"
else
  echo "✗ Upload failed (HTTP ${HTTP_STATUS})"
  echo "Response: $RESPONSE"
  exit 1
fi

echo ""
echo "→ Verifying upload — listing rules in namespace '${NAMESPACE}'..."
curl -s \
  "${GRAFANA_URL}/api/prom/rules/${NAMESPACE}" \
  -u "${PROM_USER_ID}:${GRAFANA_API_TOKEN}" | head -60

echo ""
echo "Done."
