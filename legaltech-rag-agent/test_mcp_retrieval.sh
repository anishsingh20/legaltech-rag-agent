#!/usr/bin/env bash
# Smoke test for Knowledge Bases MCP retrieval.
# Requires: DIGITALOCEAN_API_TOKEN (GenAI:read), KNOWLEDGE_BASE_ID

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ -f "${ROOT_DIR}/config.env" ]]; then
  # shellcheck disable=SC1091
  source "${ROOT_DIR}/config.env"
fi

: "${DIGITALOCEAN_API_TOKEN:?Set DIGITALOCEAN_API_TOKEN in config.env or .env}"
: "${KNOWLEDGE_BASE_ID:?Set KNOWLEDGE_BASE_ID in config.env or .env}"

echo "Initializing MCP session..."
curl -sS -X POST "https://kbaas.do-ai.run/v1/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer ${DIGITALOCEAN_API_TOKEN}" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2025-03-26",
      "capabilities": {},
      "clientInfo": {"name": "legaltech-tutorial", "version": "1.0.0"}
    }
  }' | head -c 500
echo ""

echo "Calling retrieve_knowledge_base..."
curl -sS -X POST "https://kbaas.do-ai.run/v1/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer ${DIGITALOCEAN_API_TOKEN}" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": 2,
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"retrieve_knowledge_base\",
      \"arguments\": {
        \"knowledge_base_id\": \"${KNOWLEDGE_BASE_ID}\",
        \"query\": \"What is the status of case 2024-0142?\",
        \"num_results\": 3,
        \"alpha\": 0.5
      }
    }
  }"
