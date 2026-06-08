#!/usr/bin/env bash
# Wrapper for 01_discover_prerequisites.py
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"
if [[ -f config.env ]]; then
  # shellcheck disable=SC1091
  source config.env
fi
python3 scripts/01_discover_prerequisites.py
