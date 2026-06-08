"""
LegalTech RAG agent: Serverless Inference + Knowledge Base MCP retrieval.

ADK path (optional — requires ADK Feature Preview for deploy):
  gradient agent run
  gradient agent deploy

App Platform path (no ADK):
  uvicorn serve:app --port 8080
"""

from __future__ import annotations

import os

from gradient import AsyncGradient
from gradient_adk import entrypoint, trace_llm, trace_retriever

from rag_core import generate_answer, retrieve_context, run_rag


@trace_retriever("knowledge_base")
async def _retrieve_context(query: str) -> str:
    return await retrieve_context(query)


@trace_llm("serverless_inference")
async def _generate_answer(query: str, context: str) -> str:
    return await generate_answer(query, context)


@entrypoint
async def main(input: dict, context: dict) -> dict:
    """ADK entrypoint. Expects JSON: {"prompt": "your question"}."""
    query = input.get("prompt", "").strip()
    if not query:
        return {"response": "Send a prompt field with your question."}
    return await run_rag(query)


async def smoke_test_serverless() -> None:
    """Optional local check without MCP."""
    client = AsyncGradient(
        inference_endpoint="https://inference.do-ai.run",
        model_access_key=os.environ["MODEL_ACCESS_KEY"],
    )
    result = await client.chat.completions.create(
        model=os.environ.get("INFERENCE_MODEL", "anthropic-claude-sonnet-4"),
        messages=[{"role": "user", "content": "Reply with the word READY."}],
        max_tokens=10,
    )
    print(result.choices[0].message.content)
