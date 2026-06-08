#!/usr/bin/env bash
# Run the full Knowledge Base setup pipeline in order.
# Prerequisite: copy config.env.example to config.env and fill in tokens.

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -f config.env ]]; then
  echo "Create config.env first:"
  echo "  cp config.env.example config.env"
  exit 1
fi

# shellcheck disable=SC1091
source config.env

echo "========== 01 Discover prerequisites =========="
./scripts/01_discover_prerequisites.sh

echo ""
echo "========== 02 Upload sample files to Spaces =========="
python3 scripts/02_upload_to_spaces.py

echo ""
echo "========== 03 Create Knowledge Base =========="
python3 scripts/03_create_knowledge_base.py

# Reload KNOWLEDGE_BASE_ID written by step 03
# shellcheck disable=SC1091
source config.env

echo ""
echo "========== 04 Wait for indexing =========="
python3 scripts/04_wait_for_indexing.py

echo ""
echo "========== 05 Test retrieve API =========="
./scripts/05_test_retrieve_api.sh

echo ""
echo "========== 06 Test MCP retrieval =========="
./legaltech-rag-agent/test_mcp_retrieval.sh

echo ""
echo "Setup complete. Continue with the tutorial Steps 4-6 for the ADK agent."
