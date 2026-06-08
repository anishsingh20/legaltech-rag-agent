#!/usr/bin/env python3
"""
Step 3: Create a DigitalOcean Knowledge Base via API.

Indexes the Spaces bucket configured in config.env.
Run from repo root:  source config.env && python3 scripts/03_create_knowledge_base.py

API reference:
https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

API_BASE = "https://api.digitalocean.com/v2/gen-ai"
ROOT = Path(__file__).resolve().parent.parent
CONFIG_ENV = ROOT / "config.env"


def api_request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    url = f"{API_BASE}{path}"
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code} for {method} {url}")
        print(err_body)
        sys.exit(1)


def save_kb_id(kb_id: str) -> None:
    """Append KNOWLEDGE_BASE_ID to config.env for later scripts."""
    lines: list[str] = []
    if CONFIG_ENV.exists():
        lines = CONFIG_ENV.read_text(encoding="utf-8").splitlines()

    updated: list[str] = []
    found = False
    for line in lines:
        if line.startswith("export KNOWLEDGE_BASE_ID="):
            updated.append(f'export KNOWLEDGE_BASE_ID="{kb_id}"')
            found = True
        else:
            updated.append(line)

    if not found:
        if updated and updated[-1].strip():
            updated.append("")
        updated.append("# Auto-filled by 03_create_knowledge_base.py")
        updated.append(f'export KNOWLEDGE_BASE_ID="{kb_id}"')

    CONFIG_ENV.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"Saved KNOWLEDGE_BASE_ID to {CONFIG_ENV}")


def main() -> None:
    token = os.environ.get("DIGITALOCEAN_API_TOKEN")
    project_id = os.environ.get("DO_PROJECT_ID")
    name = os.environ.get("KB_NAME", "legaltech-cases-kb")
    region = os.environ.get("KB_REGION", "tor1")
    embedding_uuid = os.environ.get(
        "EMBEDDING_MODEL_UUID", "22652c2a-79ed-11ef-bf8f-4e013e2ddde4"
    )
    vpc_uuid = os.environ.get("VPC_UUID", "db9169a0-e935-4329-9add-3ee52359105a")
    bucket = os.environ.get("SPACES_BUCKET", "legaltech-casefiles-tutorial")
    spaces_region = os.environ.get("SPACES_REGION", "tor1")
    missing = []
    if not token or "your_" in token:
        missing.append("DIGITALOCEAN_API_TOKEN")
    if not project_id or "your_" in project_id:
        missing.append("DO_PROJECT_ID")
    if missing:
        print(f"Set these in config.env: {', '.join(missing)}")
        print("Run ./scripts/01_discover_prerequisites.sh to find DO_PROJECT_ID")
        sys.exit(1)

    payload: dict = {
        "name": name,
        "embedding_model_uuid": embedding_uuid,
        "project_id": project_id,
        "region": region,
        "vpc_uuid": vpc_uuid,
        "tags": ["legaltech-tutorial"],
        "datasources": [
            {
                "spaces_data_source": {
                    "bucket_name": bucket,
                    "region": spaces_region,
                },
                "chunking_algorithm": "CHUNKING_ALGORITHM_SECTION_BASED",
                "chunking_options": {"max_chunk_size": 256},
            }
        ],
    }

    if os.environ.get("KB_RERANKING_ENABLED", "true").lower() == "true":
        payload["reranking_config"] = {
            "enabled": True,
            "model": os.environ.get("KB_RERANKING_MODEL", "bge-reranker-v2-m3"),
        }

    print("Creating knowledge base with payload:")
    print(json.dumps(payload, indent=2))
    print("")

    response = api_request("POST", "/knowledge_bases", token, payload)

    kb = response.get("knowledge_base") or response.get("knowledgeBase") or response
    kb_id = kb.get("uuid") or kb.get("id")
    kb_name = kb.get("name")
    status = kb.get("status", "provisioning")

    if not kb_id:
        print("Unexpected response:")
        print(json.dumps(response, indent=2))
        sys.exit(1)

    print(f"Knowledge base created.")
    print(f"  ID:     {kb_id}")
    print(f"  Name:   {kb_name}")
    print(f"  Status: {status}")
    print(f"  URL:    https://cloud.digitalocean.com/agent-platform/knowledge-bases/{kb_id}")

    save_kb_id(kb_id)

    print("")
    print("Indexing starts automatically. Wait before MCP tests.")
    print("Next:  source config.env && python3 scripts/04_wait_for_indexing.py")


if __name__ == "__main__":
    main()
