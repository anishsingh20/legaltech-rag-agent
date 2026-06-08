#!/usr/bin/env python3
"""
Step 4: Poll knowledge base status until indexing finishes.

Run from repo root:  source config.env && python3 scripts/04_wait_for_indexing.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

API_BASE = "https://api.digitalocean.com/v2/gen-ai"
POLL_SECONDS = int(os.environ.get("INDEX_POLL_SECONDS", "30"))
MAX_WAIT_MINUTES = int(os.environ.get("INDEX_MAX_WAIT_MINUTES", "45"))


def get_kb(token: str, kb_id: str) -> dict:
    url = f"{API_BASE}/knowledge_bases/{kb_id}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("knowledge_base") or data.get("knowledgeBase") or data


def list_jobs(token: str, kb_id: str) -> list:
    url = f"{API_BASE}/knowledge_bases/{kb_id}/indexing_jobs"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data.get("jobs") or data.get("indexing_jobs") or []
    except Exception:
        return []


def main() -> None:
    token = os.environ.get("DIGITALOCEAN_API_TOKEN")
    kb_id = os.environ.get("KNOWLEDGE_BASE_ID")

    if not token or not kb_id:
        print("Set DIGITALOCEAN_API_TOKEN and KNOWLEDGE_BASE_ID in config.env")
        sys.exit(1)

    deadline = time.time() + MAX_WAIT_MINUTES * 60
    attempt = 0

    while time.time() < deadline:
        attempt += 1
        kb = get_kb(token, kb_id)
        status = (kb.get("status") or "unknown").lower()
        phase = kb.get("phase") or kb.get("provisioning_status") or ""
        print(f"[{attempt}] status={status} phase={phase}")

        jobs = list_jobs(token, kb_id)
        if jobs:
            latest = jobs[0]
            job_status = latest.get("status") or latest.get("phase") or "unknown"
            print(f"      latest indexing job: {job_status}")

        done_states = {"active", "ready", "completed", "running"}
        if status in done_states:
            print("")
            print("Knowledge base is ready for retrieval tests.")
            print("Next:  source config.env && ./legaltech-rag-agent/test_mcp_retrieval.sh")
            return

        if status in {"failed", "error"}:
            print("Knowledge base entered a failed state. Check Activity tab in Control Panel.")
            sys.exit(1)

        time.sleep(POLL_SECONDS)

    print(f"Timed out after {MAX_WAIT_MINUTES} minutes.")
    print("Check INFERENCE -> Agent Platform -> Knowledge bases -> Activity")
    sys.exit(1)


if __name__ == "__main__":
    main()
