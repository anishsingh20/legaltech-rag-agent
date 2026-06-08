#!/usr/bin/env python3
"""
Step 1: Discover project ID, embedding models, VPC, and existing knowledge bases.
Run:  source config.env && python3 scripts/01_discover_prerequisites.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request

API = "https://api.digitalocean.com/v2"


def get(path: str, token: str) -> dict:
    req = urllib.request.Request(
        f"{API}{path}",
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    token = os.environ.get("DIGITALOCEAN_API_TOKEN")
    if not token or "your_" in token:
        print("Set DIGITALOCEAN_API_TOKEN in config.env first")
        sys.exit(1)

    region = os.environ.get("KB_REGION", "tor1")

    print("=== Projects (copy DO_PROJECT_ID from your default project) ===")
    projects = get("/projects?per_page=20", token)
    for project in projects.get("projects", []):
        suffix = " (DEFAULT)" if project.get("is_default") else ""
        print(f"  {project['id']}  {project['name']}{suffix}")

    print("")
    print("=== Embedding models (vectorization) ===")
    models = get(
        "/gen-ai/models?usecases=MODEL_USECASE_KNOWLEDGEBASE&per_page=50", token
    )
    for model in models.get("models", []):
        print(f"  {model.get('uuid')}  {model.get('name')}")

    print("")
    print(f"=== VPC for region {region} ===")
    vpcs = get("/vpcs?per_page=50", token)
    for vpc in vpcs.get("vpcs", []):
        if vpc.get("region") == region:
            print(f"  {vpc['id']}  {vpc['name']}  region={vpc['region']}")

    print("")
    print("=== Existing knowledge bases ===")
    kbs = get("/gen-ai/knowledge_bases", token)
    items = kbs.get("knowledge_bases") or kbs.get("knowledgeBases") or []
    if not items:
        print("  (none yet)")
    for kb in items:
        kb_id = kb.get("uuid") or kb.get("id")
        print(f"  {kb_id}  {kb.get('name')}  status={kb.get('status', 'unknown')}")

    print("")
    print("Next: set DO_PROJECT_ID in config.env, then run:")
    print("  python3 scripts/02_upload_to_spaces.py")


if __name__ == "__main__":
    main()
