"""
FastAPI RAG service — deploy without Gradient ADK.

Run locally:
  uvicorn serve:app --host 0.0.0.0 --port 8080

Same request shape as ADK: POST /run with {"prompt": "..."}
"""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from rag_core import run_rag

load_dotenv()

app = FastAPI(
    title="LegalTech RAG Agent",
    description="Knowledge Bases retrieval + DigitalOcean Serverless Inference",
    version="1.0.0",
)


class RunRequest(BaseModel):
    prompt: str = Field(..., description="Attorney research question")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run")
async def run(body: RunRequest) -> dict[str, Any]:
    query = body.prompt.strip()
    if not query:
        raise HTTPException(status_code=400, detail="prompt is required")

    for var in ("KNOWLEDGE_BASE_ID", "DIGITALOCEAN_API_TOKEN", "MODEL_ACCESS_KEY"):
        if not os.environ.get(var):
            raise HTTPException(
                status_code=500,
                detail=f"Missing required environment variable: {var}",
            )

    try:
        return await run_rag(query)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
