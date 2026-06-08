#!/usr/bin/env bash
# Step 5: Test retrieval through the Knowledge Base REST API (before MCP).
# Run:  source config.env && ./scripts/05_test_retrieve_api.sh

set -euo pipefail

: "${DIGITALOCEAN_API_TOKEN:?Set DIGITALOCEAN_API_TOKEN in config.env}"
: "${KNOWLEDGE_BASE_ID:?Set KNOWLEDGE_BASE_ID in config.env}"

QUERY="${1:-What is the status of case 2024-0142?}"
NUM_RESULTS="${NUM_RESULTS:-5}"
ALPHA="${RETRIEVAL_ALPHA:-0.5}"

echo "Query: ${QUERY}"
echo ""

curl -sS -X POST "https://kbaas.do-ai.run/v1/${KNOWLEDGE_BASE_ID}/retrieve" \
  -H "Authorization: Bearer ${DIGITALOCEAN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"query\": \"${QUERY}\",
    \"num_results\": ${NUM_RESULTS},
    \"alpha\": ${ALPHA}
  }" | python3 -m json.tool

echo ""
echo "If total_results > 0, run ./legaltech-rag-agent/test_mcp_retrieval.sh next."
