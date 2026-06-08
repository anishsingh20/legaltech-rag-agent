"""
Shared RAG logic: Knowledge Base retrieval + Serverless Inference.

Used by:
  - main.py (optional ADK path via gradient agent run/deploy)
  - serve.py (FastAPI — deploy to App Platform without ADK)
"""

from __future__ import annotations

import json
import os
from typing import Any

import httpx
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI

SYSTEM_PROMPT = """You are a legal research assistant for a solo law firm.
Answer only from the retrieved case file context.
Cite matter IDs and dates when present.
If context is missing, say you do not have enough indexed material.
Do not provide client-facing legal advice."""


def _build_llm() -> ChatOpenAI:
    return ChatOpenAI(
        model=os.environ.get("INFERENCE_MODEL", "anthropic-claude-sonnet-4"),
        api_key=os.environ.get("MODEL_ACCESS_KEY"),
        base_url="https://inference.do-ai.run/v1",
        temperature=0.1,
        max_tokens=800,
    )


async def retrieve_context_mcp(query: str) -> str:
    """Retrieve via Knowledge Bases MCP (best for Cursor / LangChain tool demos)."""
    kb_id = os.environ["KNOWLEDGE_BASE_ID"]
    token = os.environ["DIGITALOCEAN_API_TOKEN"]
    num_results = int(os.environ.get("NUM_RESULTS", "5"))

    client = MultiServerMCPClient(
        {
            "digitalocean-kb": {
                "transport": "streamable_http",
                "url": "https://kbaas.do-ai.run/v1/mcp",
                "headers": {
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json, text/event-stream",
                },
            }
        }
    )

    tools = await client.get_tools()
    retrieve_tool = next(t for t in tools if t.name == "retrieve_knowledge_base")

    raw = await retrieve_tool.ainvoke(
        {
            "knowledge_base_id": kb_id,
            "query": query,
            "num_results": num_results,
            "alpha": float(os.environ.get("RETRIEVAL_ALPHA", "0.5")),
        }
    )

    if isinstance(raw, str):
        return raw
    return json.dumps(raw, indent=2)


async def retrieve_context_rest(query: str) -> str:
    """Retrieve via Knowledge Bases REST API (stable for App Platform / production)."""
    kb_id = os.environ["KNOWLEDGE_BASE_ID"]
    token = os.environ["DIGITALOCEAN_API_TOKEN"]
    num_results = int(os.environ.get("NUM_RESULTS", "5"))
    alpha = float(os.environ.get("RETRIEVAL_ALPHA", "0.5"))

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://kbaas.do-ai.run/v1/{kb_id}/retrieve",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "num_results": num_results,
                "alpha": alpha,
            },
        )
        response.raise_for_status()
        return json.dumps(response.json(), indent=2)


async def retrieve_context(query: str) -> str:
    """Pick retrieval transport from RETRIEVAL_MODE (rest default for hosted deploy)."""
    mode = os.environ.get("RETRIEVAL_MODE", "rest").lower()
    if mode == "mcp":
        return await retrieve_context_mcp(query)
    return await retrieve_context_rest(query)


async def generate_answer(query: str, context: str) -> str:
    llm = _build_llm()
    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(
            content=(
                f"Retrieved context:\n{context}\n\n"
                f"Attorney question: {query}\n\n"
                "Answer with bullet points and cite matter IDs."
            )
        ),
    ]
    response = await llm.ainvoke(messages)
    return response.content


async def run_rag(query: str) -> dict[str, Any]:
    """End-to-end RAG: retrieve chunks, then answer with Serverless Inference."""
    retrieved = await retrieve_context(query)
    answer = await generate_answer(query, retrieved)
    return {
        "response": answer,
        "retrieval_preview": retrieved[:1200],
        "knowledge_base_id": os.environ.get("KNOWLEDGE_BASE_ID"),
        "model": os.environ.get("INFERENCE_MODEL", "anthropic-claude-sonnet-4"),
        "retrieval_mode": os.environ.get("RETRIEVAL_MODE", "rest"),
    }
