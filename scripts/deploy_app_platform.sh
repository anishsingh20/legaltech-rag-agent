#!/usr/bin/env bash
# Generate .do/app.deploy.yaml from config.env and create/update App Platform app.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f config.env ]]; then
  echo "Missing config.env — copy config.env.example and fill in values." >&2
  exit 1
fi

# shellcheck disable=SC1091
source config.env

for var in DIGITALOCEAN_API_TOKEN MODEL_ACCESS_KEY KNOWLEDGE_BASE_ID DO_PROJECT_ID; do
  if [[ -z "${!var:-}" ]]; then
    echo "config.env must set $var" >&2
    exit 1
  fi
done

export DOCTL_ACCESS_TOKEN="${DIGITALOCEAN_API_TOKEN}"

python3 <<PY
from pathlib import Path
import os

root = Path("${ROOT}")
template = (root / ".do" / "app.yaml").read_text()
for val in [
    os.environ["MODEL_ACCESS_KEY"],
    os.environ["DIGITALOCEAN_API_TOKEN"],
    os.environ["KNOWLEDGE_BASE_ID"],
]:
    template = template.replace("REPLACE_ME", val, 1)
(root / ".do" / "app.deploy.yaml").write_text(template)
print("Wrote .do/app.deploy.yaml")
PY

if doctl apps list --format ID,Spec.Name --no-header 2>/dev/null | awk '$2=="legaltech-rag-agent"{exit 0} END{exit 1}'; then
  APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | awk '$2=="legaltech-rag-agent"{print $1; exit}')
  echo "Updating existing app $APP_ID ..."
  doctl apps update "$APP_ID" --spec .do/app.deploy.yaml --wait
else
  echo "Creating new app legaltech-rag-agent ..."
  doctl apps create --spec .do/app.deploy.yaml --project-id "$DO_PROJECT_ID" --wait
fi

APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | awk '$2=="legaltech-rag-agent"{print $1; exit}')
echo ""
echo "App ID: $APP_ID"
doctl apps get "$APP_ID" --format ID,DefaultIngress,ActiveDeployment.Phase
