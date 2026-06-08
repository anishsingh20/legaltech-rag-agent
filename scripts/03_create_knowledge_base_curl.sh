#!/usr/bin/env bash
# Alternative to 03_create_knowledge_base.py: create KB with curl + jq.
# Run:  source config.env && ./scripts/03_create_knowledge_base_curl.sh

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ -f config.env ]]; then
  # shellcheck disable=SC1091
  source config.env
fi

: "${DIGITALOCEAN_API_TOKEN:?Set DIGITALOCEAN_API_TOKEN}"
: "${DO_PROJECT_ID:?Set DO_PROJECT_ID}"

PAYLOAD_FILE="${ROOT_DIR}/payloads/create_knowledge_base.json"
TMP_PAYLOAD="$(mktemp)"

python3 - <<PY
import json, os
from pathlib import Path
data = json.loads(Path("${PAYLOAD_FILE}").read_text())
data["project_id"] = os.environ["DO_PROJECT_ID"]
data["name"] = os.environ.get("KB_NAME", data["name"])
data["embedding_model_uuid"] = os.environ.get(
    "EMBEDDING_MODEL_UUID", data["embedding_model_uuid"]
)
data["region"] = os.environ.get("KB_REGION", data["region"])
data["vpc_uuid"] = os.environ.get("VPC_UUID", data["vpc_uuid"])
data["datasources"][0]["spaces_data_source"]["bucket_name"] = os.environ.get(
    "SPACES_BUCKET", data["datasources"][0]["spaces_data_source"]["bucket_name"]
)
data["datasources"][0]["spaces_data_source"]["region"] = os.environ.get(
    "SPACES_REGION", data["datasources"][0]["spaces_data_source"]["region"]
)
Path("${TMP_PAYLOAD}").write_text(json.dumps(data, indent=2))
print(json.dumps(data, indent=2))
PY

echo ""
echo "Sending POST to gen-ai/knowledge_bases ..."

RESPONSE="$(curl -sS -X POST "https://api.digitalocean.com/v2/gen-ai/knowledge_bases" \
  -H "Authorization: Bearer ${DIGITALOCEAN_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @"${TMP_PAYLOAD}")"

rm -f "${TMP_PAYLOAD}"
echo "${RESPONSE}" | python3 -m json.tool

KB_ID="$(echo "${RESPONSE}" | python3 -c "
import json, sys
d = json.load(sys.stdin)
kb = d.get('knowledge_base') or d.get('knowledgeBase') or d
print(kb.get('uuid') or kb.get('id') or '')
")"

if [[ -z "${KB_ID}" ]]; then
  echo "Create failed. Check response above."
  exit 1
fi

echo ""
echo "Knowledge base ID: ${KB_ID}"

if grep -q '^export KNOWLEDGE_BASE_ID=' config.env 2>/dev/null; then
  sed -i.bak "s|^export KNOWLEDGE_BASE_ID=.*|export KNOWLEDGE_BASE_ID=\"${KB_ID}\"|" config.env
  rm -f config.env.bak
else
  printf '\nexport KNOWLEDGE_BASE_ID="%s"\n' "${KB_ID}" >> config.env
fi

echo "Saved KNOWLEDGE_BASE_ID to config.env"
echo "Next:  source config.env && python3 scripts/04_wait_for_indexing.py"
