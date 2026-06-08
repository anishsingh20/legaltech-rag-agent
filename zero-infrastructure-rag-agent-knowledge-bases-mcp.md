---
title: "Zero-Infrastructure RAG Agent with Knowledge Bases + MCP"
description: "Upload case files to Spaces, index them with DigitalOcean Knowledge Bases, call retrieval through MCP, and deploy a LegalTech research agent with Serverless Inference and ADK."
conclusion_cta: null
right_side_nav_cta: null
draft: null
header_url: null
tutorial_type: tutorial
state: draft
language: en
published_at: null
last_validated_at: null
follow_up_questions_enabled_at: null
comments_locked_at: null
raw_html_allowed_in_markdown_at: null
featured_at: null
authors:
  - slug: asinghwalia
editors: []
translators: []
primary_tag: ai-ml
tags:
  - inference
  - knowledge-bases
  - mcp
  - rag
  - agent-development-kit
teams:
  - do-writers
origins:
  - in-house
---

## Introduction

A solo LegalTech founder has 10,000+ internal case files. The product needs an AI assistant that returns grounded answers with source references. The founder does not want to operate a vector database, an embedding service, or a reranker on day one.

**DigitalOcean Knowledge Bases** is a managed RAG pipeline. You point at files in [Spaces](https://www.digitalocean.com/products/spaces), and the platform handles chunking, embedding, and storage in [Managed OpenSearch](https://docs.digitalocean.com/products/databases/opensearch/). Retrieval is exposed as an MCP tool at `https://kbaas.do-ai.run/v1/mcp`, so agent frameworks call one function instead of wiring five services.

This tutorial differs from older RAG walkthroughs that assemble LangChain + Chroma yourself. Here you use DO-native infrastructure only: Spaces, Knowledge Bases, MCP, [Serverless Inference](https://docs.digitalocean.com/products/inference/how-to/use-serverless-inference/), and the [Agent Development Kit (ADK)](https://docs.digitalocean.com/products/inference/getting-started/use-adk/).

**Product:** DigitalOcean Inference (Agent Platform, Knowledge Bases, Serverless Inference, MCP)  
**Use case:** Legal matter research over private case files  
**Context:** Solo founder or solutions engineer shipping a grounded assistant in days, not weeks

## Key takeaways

- Knowledge Bases indexes PDF, Markdown, HTML, and 15+ text formats from Spaces buckets without you running vector infrastructure.
- The Knowledge Bases MCP endpoint exposes `retrieve_knowledge_base` for hybrid search with 1 to 25 results per call.
- MCP retrieval billing matches the [Knowledge Base retrieve API](https://docs.digitalocean.com/products/inference/details/pricing/#knowledge-bases): you pay embedding tokens for query vectorization plus optional reranking tokens.
- Answer generation is separate. RAG Playground and your ADK agent bill [Serverless Inference](https://docs.digitalocean.com/products/inference/details/pricing/#serverless-inference) per token (for example, Claude Sonnet 4.6 at $3.00 per 1M input tokens and $15.00 per 1M output tokens for prompts up to 200K tokens).
- Agent creation on the Agent Platform is free. You pay for model usage, indexing, storage, and retrieval.
- For production LegalTech workloads, start in **TOR1**. Most Agent Platform infrastructure runs there per [Knowledge Base docs](https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/).

## When to use Knowledge Bases + MCP and when not to

| Knowledge Bases + MCP is a good fit | Try something else |
| --- | --- |
| Static or semi-static document corpora (case files, manuals, policies) | Live transactional data (CRM rows, ticket state) |
| You want hybrid semantic + keyword retrieval with optional reranking | You only need a single API call with no document grounding |
| You want MCP-standard tool access for Cursor, LangChain, or custom agents | You need sub-10ms retrieval at massive QPS on custom hardware |
| You want managed OpenSearch and Spaces storage | You must run a self-hosted vector DB for policy reasons |
| Prototype to production on one cloud | You already operate a mature RAG stack you prefer to keep |

For the RAG vs MCP decision tree at the pattern level, see [Guide to RAG and MCP](https://www.digitalocean.com/community/tutorials/engineers-guide-rag-vs-mcp-llms). This tutorial uses RAG for document grounding and MCP as the tool transport.

## Prerequisites

Before you start, confirm you have:

- A [DigitalOcean account](https://www.digitalocean.com/pricing).
- **Inference** and **Agent Platform** access in the [Control Panel](https://cloud.digitalocean.com).
- A [personal access token](https://docs.digitalocean.com/reference/api/create-personal-access-token/) with `GenAI:read` for retrieval and MCP, plus `genai` CRUD scopes if you deploy with ADK.
- A **Model Access Key** from **INFERENCE** → **Serverless Inference** → **Model Access Keys**, or a personal access token with Serverless Inference access (some accounts can use the same PAT as `MODEL_ACCESS_KEY` when dedicated model keys are unavailable).
- **ADK Feature Preview** (optional) on the [Feature Preview page](https://cloud.digitalocean.com/account/feature-preview) only if you use `gradient agent deploy`. Otherwise use `serve.py` + App Platform or RAG Playground.
- **Knowledge Base Enhancements** preview enabled for advanced chunking and the retrieve endpoint (recommended).
- Python 3.10+ for local ADK testing.
- Optional: [DigitalOcean MCP server](https://docs.digitalocean.com/reference/mcp/configure-mcp/) in Cursor to list models and Spaces keys during setup.

**Lab tip:** Use a sandbox project. Do not upload real client PII for this walkthrough. The sample files in this repo are fictional.

## A quick map of terms

| Term | Think of it as |
| --- | --- |
| RAG | Retrieve relevant document chunks, then ask the LLM to answer using those chunks |
| Knowledge Base | Managed index over your files or URLs |
| MCP | A standard way for an LLM agent to call tools like `retrieve_knowledge_base` |
| Spaces | S3-compatible object storage for your raw case files |
| Serverless Inference | Pay-per-token access to catalog models (Claude, Llama, and others) |
| ADK | SDK + CLI to run and deploy agent code on DO agent hosting |
| Reranking | Reorders retrieved chunks so the best passages rise to the top |
| `alpha` | Retrieval knob: `0` keyword, `1` semantic, `0.5` hybrid (default) |

## What you will build

```text
  sample case files (Markdown/PDF)
           |
           v
    DigitalOcean Spaces bucket
           |
           v
    Knowledge Base (chunk + embed + OpenSearch)
           |
     +-----+-----+
     |           |
     v           v
 MCP retrieve   RAG Playground (manual QA)
 https://kbaas.do-ai.run/v1/mcp
     |
     v
 ADK agent + Serverless Inference (Claude Sonnet or Llama)
     |
     v
 Agent hosting URL for production queries
```

By the end you will have:

1. A Spaces bucket with fictional LegalTech case files.
2. A Knowledge Base in status **Active** with indexed chunks.
3. A working MCP retrieval call against `retrieve_knowledge_base`.
4. A LangChain + ADK agent that retrieves through MCP and answers through Serverless Inference.
5. A RAG Playground session with reranking tuned for precision.
6. A deployed agent endpoint you reuse in your app.

## How to use this tutorial

- Start with `SETUP.md` in this folder for a numbered script pipeline you run copy by copy.
- Copy `config.env.example` to `config.env` before any script. Never commit `config.env`.
- Wait for indexing to finish before MCP tests. Provisioning often takes five minutes or longer per [Knowledge Base docs](https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/).
- Run `test_mcp_retrieval.sh` before `gradient agent deploy`. Retrieval must work first.
- If you already have a Knowledge Base, start at *Step 3*.

## Repo layout

```text
Zero-Infrastructure RAG Agent/
├── SETUP.md                          # Numbered runbook (start here)
├── config.env.example                # Copy to config.env
├── sample-case-files/                # Fictional LegalTech Markdown files
├── scripts/
│   ├── 01_discover_prerequisites.py  # List project UUID, models, VPCs
│   ├── 02_upload_to_spaces.py        # Upload sample files to Spaces
│   ├── 03_create_knowledge_base.py   # Create KB via API
│   ├── 04_wait_for_indexing.py       # Poll until indexing completes
│   ├── 05_test_retrieve_api.sh       # REST retrieval smoke test
│   └── run_all.sh                    # Run steps 01-06 in order
└── legaltech-rag-agent/
    ├── main.py                       # ADK agent (MCP + Serverless Inference)
    └── test_mcp_retrieval.sh         # MCP retrieval smoke test
```

## The six steps at a glance

| Step | Goal | Primary command or path |
| --- | --- | --- |
| 0 | Configure secrets | `cp config.env.example config.env` |
| 1 | Stage case files in Spaces | `python3 scripts/02_upload_to_spaces.py` |
| 2 | Create and index a Knowledge Base | `python3 scripts/03_create_knowledge_base.py` |
| 3 | Test MCP retrieval | `./legaltech-rag-agent/test_mcp_retrieval.sh` |
| 4 | Register MCP in your agent | `legaltech-rag-agent/main.py` |
| 5 | Point agent at Serverless Inference | `.env` + model access key |
| 6 | RAG Playground + deploy | **RAG Playground** + `gradient agent deploy` |

---

## Step 0: Configure your environment file

Every script in this tutorial reads from one file so you do not chase variables across terminals.

**1. Copy the template:**

```bash
cd "Zero-Infrastructure RAG Agent"
cp config.env.example config.env
```

**2. Open `config.env` and set these values:**

| Variable | Where to get it |
| --- | --- |
| `DIGITALOCEAN_API_TOKEN` | [API Tokens](https://cloud.digitalocean.com/account/api/tokens) with `genai` + `GenAI:read` |
| `DO_PROJECT_ID` | Output of `01_discover_prerequisites.sh` (default project UUID) |
| `SPACES_ACCESS_KEY_ID` | Control Panel → **Spaces** → **Access Keys**, or MCP `spaces-key-create` |
| `SPACES_SECRET_ACCESS_KEY` | Shown once when you create the Spaces key |
| `MODEL_ACCESS_KEY` | **INFERENCE** → **Serverless Inference** → **Model Access Keys** |

**3. Load the file before each step:**

```bash
source config.env
```

The template already includes verified defaults for this lab:

- `EMBEDDING_MODEL_UUID=22652c2a-79ed-11ef-bf8f-4e013e2ddde4` (All MiniLM L6 v2)
- `VPC_UUID=db9169a0-e935-4329-9add-3ee52359105a` (default-tor1)
- `KB_REGION=tor1`

**4. Discover your project UUID:**

```bash
chmod +x scripts/*.sh legaltech-rag-agent/test_mcp_retrieval.sh
./scripts/01_discover_prerequisites.sh
```

Copy the default project UUID into `DO_PROJECT_ID` in `config.env`.

---

## Step 1: Upload case files to a Spaces bucket

Your raw files live in Spaces. The Knowledge Base pulls from the bucket and indexes supported formats (`.md`, `.pdf`, `.html`, `.docx`, and others listed in the [Knowledge Base docs](https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/)).

### Prepare sample files for the lab

This tutorial includes four fictional Markdown files under `sample-case-files/`:

- `case-2024-0142-nda-breach.md`
- `case-2023-0891-employment.md`
- `case-2024-0310-ip-licensing.md`
- `firm-retrieval-policy.md`

For a 10,000-file production corpus, the same pattern applies. Organize one bucket per client or per matter class. The docs recommend five or fewer buckets per knowledge base for indexing performance.

### Create a Spaces bucket

1. Open the [Control Panel](https://cloud.digitalocean.com) → **Spaces Object Storage** → **Create Bucket**.
2. Choose a region. Use **TOR1** if you plan to attach agents in Agent Platform.
3. Name the bucket `legaltech-casefiles-tutorial` (or your own name).
4. Upload the sample files from `sample-case-files/`.

### Upload with the included Python script (recommended)

**1. Install the upload dependency:**

```bash
pip install -r scripts/requirements.txt
```

**2. Run the upload script:**

```bash
source config.env
python3 scripts/02_upload_to_spaces.py
```

**What this script does:** It connects to Spaces with your S3-compatible keys, creates the bucket if missing, and uploads all four `.md` files under `cases/`.

**Expected output:**

```text
Bucket exists: legaltech-casefiles-tutorial
Uploading 4 files to s3://legaltech-casefiles-tutorial/cases/
  uploaded cases/case-2024-0142-nda-breach.md
  uploaded cases/case-2023-0891-employment.md
  uploaded cases/case-2024-0310-ip-licensing.md
  uploaded cases/firm-retrieval-policy.md
Upload complete.
```

Each file upload is a plain copy. No embedding happens until Step 2.

### Upload with AWS CLI (optional alternative)

```bash
aws s3 cp sample-case-files/ s3://legaltech-casefiles-tutorial/cases/ \
  --recursive \
  --endpoint-url https://tor1.digitaloceanspaces.com
```

### Verify with DigitalOcean MCP (optional)

If you use the [DigitalOcean MCP server](https://docs.digitalocean.com/reference/mcp/configure-mcp/) in Cursor, list Spaces access keys with `spaces-key-list`. Create a dedicated key with `spaces-key-create` if you need programmatic upload access.

---

## Step 2: Create a Knowledge Base via API

Now you turn the bucket into a searchable index. This tutorial uses the [DigitalOcean GenAI API](https://docs.digitalocean.com/reference/api/reference/gradientai-platform/) so every step is reproducible from your terminal.

### What gets created

The API call provisions:

1. A Knowledge Base named `legaltech-cases-kb`
2. A new OpenSearch database (auto-sized) in TOR1
3. An indexing job over your Spaces bucket
4. Optional reranking with `bge-reranker-v2-m3`

### Choose an embeddings model

You cannot change the embeddings model after creation.

| Model | UUID (catalog) | Indexing price (per docs) |
| --- | --- | --- |
| All MiniLM L6 v2 (lab default) | `22652c2a-79ed-11ef-bf8f-4e013e2ddde4` | $0.009 per 1M tokens |
| GTE Large EN v1.5 | `22653204-79ed-11ef-bf8f-4e013e2ddde4` | $0.09 per 1M tokens |
| Bge M3 | `78836a83-26d0-11f1-b074-4e013e2ddde4` | $0.02 per 1M tokens |

List models yourself:

```bash
source config.env
curl -sS "https://api.digitalocean.com/v2/gen-ai/models?usecases=MODEL_USECASE_KNOWLEDGEBASE" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" | python3 -m json.tool
```

### Create the Knowledge Base

**1. Run the create script:**

```bash
source config.env
python3 scripts/03_create_knowledge_base.py
```

**What this script does:** It sends `POST https://api.digitalocean.com/v2/gen-ai/knowledge_bases` with your Spaces bucket as a data source, section-based chunking, and reranking enabled. On success, it writes `KNOWLEDGE_BASE_ID` into `config.env`.

**2. Inspect the JSON payload (for learning):**

The script sends a body equivalent to:

```json
{
  "name": "legaltech-cases-kb",
  "embedding_model_uuid": "22652c2a-79ed-11ef-bf8f-4e013e2ddde4",
  "project_id": "YOUR_DO_PROJECT_ID",
  "region": "tor1",
  "vpc_uuid": "db9169a0-e935-4329-9add-3ee52359105a",
  "tags": ["legaltech-tutorial"],
  "datasources": [
    {
      "spaces_data_source": {
        "bucket_name": "legaltech-casefiles-tutorial",
        "region": "tor1"
      },
      "chunking_algorithm": "CHUNKING_ALGORITHM_SECTION_BASED",
      "chunking_options": { "max_chunk_size": 256 }
    }
  ],
  "reranking_config": {
    "enabled": true,
    "model": "bge-reranker-v2-m3"
  }
}
```

**3. Expected output:**

```text
Knowledge base created.
  ID:     123e4567-e89b-12d3-a456-426614174000
  Name:   legaltech-cases-kb
  Status: provisioning
Saved KNOWLEDGE_BASE_ID to config.env
```

Replace the example UUID with the value from your account.

**Alternative (curl only):** If you prefer shell over Python for the create call:

```bash
source config.env
./scripts/03_create_knowledge_base_curl.sh
```

The curl script reads `payloads/create_knowledge_base.json`, injects your `DO_PROJECT_ID`, and saves the returned UUID to `config.env`.

### Wait for indexing

**1. Poll until the knowledge base is ready:**

```bash
source config.env
python3 scripts/04_wait_for_indexing.py
```

The script checks status every 30 seconds for up to 45 minutes.

**2. Confirm in the Control Panel (optional):**

**INFERENCE** → **Agent Platform** → **Knowledge bases** → `legaltech-cases-kb` → **Activity**

Status values include **Completed**, **Partially Completed**, and **Failed** per the [Activity docs](https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/#activity).

### Test REST retrieval before MCP

```bash
source config.env
./scripts/05_test_retrieve_api.sh
```

Pass a custom query:

```bash
./scripts/05_test_retrieve_api.sh "What is the litigation budget for case 2024-0310?"
```

**What a good response looks like:** JSON with `total_results` greater than zero and chunks that mention `$320,000` or `Lumen Bio`.

### Step 2B: Control Panel alternative (optional)

If you prefer the UI, skip `03_create_knowledge_base.py` and create the knowledge base manually:

1. **INFERENCE** → **Agent Platform** → **Knowledge bases** → **Create Knowledge Base**
2. Select an embeddings model and optional reranking model
3. **Pull from a Spaces bucket or folder** → select `legaltech-casefiles-tutorial`
4. **Create new** OpenSearch database in **TOR1**
5. Click **Create knowledge base**

Then copy the UUID from:

```text
https://cloud.digitalocean.com/agent-platform/knowledge-bases/{UUID}
```

Add it to `config.env`:

```bash
export KNOWLEDGE_BASE_ID="your_uuid_here"
```

List knowledge bases with the API:

```bash
curl -sS -X GET "https://api.digitalocean.com/v2/gen-ai/knowledge_bases" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" | python3 -m json.tool
```

---

## Step 3: Enable MCP integration and test retrieval

Knowledge Bases exposes retrieval through a dedicated MCP server. This endpoint is separate from the general DigitalOcean MCP servers (Droplets, Apps, and so on). The URL is:

```text
https://kbaas.do-ai.run/v1/mcp
```

Auth requires a personal access token with `GenAI:read` scope. Retrieval through MCP is billed the same as direct retrieve API calls per [pricing docs](https://docs.digitalocean.com/products/inference/details/pricing/#knowledge-bases).

### Supported MCP tool

| Tool | Purpose |
| --- | --- |
| `retrieve_knowledge_base` | Hybrid search over one knowledge base, 1 to 25 results |

Arguments:

- `knowledge_base_id` (required): your UUID
- `query` (required): attorney question text
- `num_results` (required): 1 to 25
- `alpha` (optional): `0.5` default hybrid
- `filters` (optional): metadata filters on `item_name`, `page_number`, and other fields

Full reference: [Knowledge Bases MCP Tools](https://docs.digitalocean.com/reference/mcp/kbaas-mcp-tools/).

### Configure MCP in Cursor (optional)

Add this block to your MCP client config per [Configure Remote MCP](https://docs.digitalocean.com/reference/mcp/configure-mcp/):

```json
{
  "mcpServers": {
    "knowledge-bases": {
      "url": "https://kbaas.do-ai.run/v1/mcp",
      "headers": {
        "Authorization": "Bearer <your_api_token_with_genai_read>"
      }
    }
  }
}
```

### Smoke test with the included shell script

From `legaltech-rag-agent/`:

```bash
export DIGITALOCEAN_API_TOKEN="your_token"
export KNOWLEDGE_BASE_ID="your_kb_uuid"
./test_mcp_retrieval.sh
```

The script does two calls:

1. `initialize` the MCP session.
2. `tools/call` for `retrieve_knowledge_base` with the query `What is the status of case 2024-0142?`.

**What a good response looks like:** JSON with `total_results` greater than zero and chunks mentioning matter `2024-0142` or the Meridian Analytics NDA breach summary. Each result should include `text_content` and `metadata` such as `source` or `page`.

**If you see zero results:** Indexing is still running, the bucket path is wrong, or the query needs a lower `alpha` for exact matter ID keyword matching. Check the **Activity** tab first. Try `alpha: 0` for ID-heavy lookups.

### Manual curl example (single call)

```bash
curl -X POST "https://kbaas.do-ai.run/v1/mcp" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "retrieve_knowledge_base",
      "arguments": {
        "knowledge_base_id": "YOUR_KB_UUID",
        "query": "What damages are claimed in case 2024-0142?",
        "num_results": 5,
        "alpha": 0.5
      }
    }
  }'
```

### Filter retrieval to one case file (precision pattern)

When an attorney works one matter, filter by filename metadata:

```json
{
  "filters": {
    "equals": {
      "key": "item_name",
      "value": "case-2024-0142-nda-breach.md"
    }
  }
}
```

This pattern mirrors the **Retrieve** tab filters in the Control Panel described in [test knowledge base retrieval docs](https://docs.digitalocean.com/products/inference/how-to/test-knowledge-base-retrieval/).

---

## Step 4: Register the MCP tool in your ADK agent

With retrieval confirmed, wire the tool into agent code. The ADK accepts LangChain, LangGraph, or custom Python. This example uses `langchain-mcp-adapters` plus `gradient-adk`.

### Initialize the agent project

```bash
pip install gradient-adk
gradient agent init
```

When prompted, choose a workspace name like `legaltech-rag` and deployment name `development`.

Replace the generated `main.py` with the tutorial version in `legaltech-rag-agent/main.py`, or copy the core pattern below.

### Understand the agent flow

```text
User prompt
    -> MCP retrieve_knowledge_base
    -> format chunks as context
    -> Serverless Inference chat completion
    -> grounded answer JSON
```

### Core code walkthrough

**1. Imports and system prompt**

The agent imports ADK decorators, LangChain messages, the MCP client, and a LangChain OpenAI-compatible client pointed at DigitalOcean inference.

```python
from gradient_adk import entrypoint, trace_llm, trace_retriever
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI
```

`SYSTEM_PROMPT` tells the model to answer only from retrieved context and to cite matter IDs. This reduces hallucinated case law references.

**2. Serverless Inference client**

```python
ChatOpenAI(
    model=os.environ.get("INFERENCE_MODEL", "anthropic-claude-sonnet-4.6"),
    api_key=os.environ.get("MODEL_ACCESS_KEY"),
    base_url="https://inference.do-ai.run/v1",
    temperature=0.1,
    max_tokens=800,
)
```

`MODEL_ACCESS_KEY` is the Serverless Inference credential. Prefer a dedicated key from **INFERENCE** → **Serverless Inference** → **Model Access Keys**. If the model-key API is retired on your account, a personal access token with inference access can work as `MODEL_ACCESS_KEY` in lab setups. `base_url` makes LangChain speak the OpenAI-compatible DigitalOcean API.

**3. MCP client for Knowledge Bases**

```python
MultiServerMCPClient({
    "digitalocean-kb": {
        "transport": "streamable_http",
        "url": "https://kbaas.do-ai.run/v1/mcp",
        "headers": {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json, text/event-stream",
        },
    }
})
```

`streamable_http` matches the Streamable HTTP transport described in the [MCP tools docs](https://docs.digitalocean.com/reference/mcp/kbaas-mcp-tools/). The client loads `retrieve_knowledge_base` as a LangChain tool.

**4. Retrieval function with tracing**

`@trace_retriever("knowledge_base_mcp")` records retrieval spans in ADK observability. Inside, the code calls:

```python
await retrieve_tool.ainvoke({
    "knowledge_base_id": kb_id,
    "query": query,
    "num_results": num_results,
    "alpha": float(os.environ.get("RETRIEVAL_ALPHA", "0.5")),
})
```

**5. Generation function**

`@trace_llm("serverless_inference")` wraps the LangChain `ainvoke` call that sends retrieved chunks plus the user question to the model.

**6. ADK entrypoint**

```python
@entrypoint
async def main(input: dict, context: dict) -> dict:
    query = input.get("prompt", "").strip()
    retrieved = await _retrieve_context(query)
    answer = await _generate_answer(query, retrieved)
    return {"response": answer, "retrieval_preview": retrieved[:1200]}
```

ADK expects this shape for HTTP `POST /run` calls.

### Environment file

Copy `.env.example` to `.env`:

```bash
cat > .env <<'EOF'
MODEL_ACCESS_KEY=your_model_access_key
DIGITALOCEAN_API_TOKEN=your_personal_access_token
KNOWLEDGE_BASE_ID=your_knowledge_base_uuid
INFERENCE_MODEL=anthropic-claude-sonnet-4.6
NUM_RESULTS=5
RETRIEVAL_ALPHA=0.5
EOF
```

Add `.env` to `.gitignore`. Never commit tokens.

### Install dependencies

```bash
pip install -r requirements.txt
```

`requirements.txt` pins `gradient-adk`, `langchain-mcp-adapters`, and `langchain-openai`.

### Run locally

```bash
export $(grep -v '^#' .env | xargs)
gradient agent run
```

Test with curl:

```bash
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize case 2023-0891 and list the next deposition date."}'
```

**Expected behavior:** The response mentions Vega Software, Jordan Ellis, and the HR director deposition on 2024-08-14 if those chunks ranked highly.

---

## Step 5: Point the agent at a Serverless Inference model

Retrieval quality and answer quality are separate choices. You pick the inference model for generation here.

### Choose a model

| Model | Input / output (per docs) | When to pick it |
| --- | --- | --- |
| Claude Sonnet 4.6 | $3.00 / $15.00 per 1M tokens (≤200K prompt) | Default for nuanced legal summaries |
| Llama 3.3 Instruct 70B | $0.65 / $0.65 per 1M tokens | Lower cost drafts and internal tools |

List models with the DigitalOcean MCP `inference-model-catalog-search` tool or the Control Panel **Model Catalog**. During tutorial prep, a search for `claude sonnet` returned UUIDs for Anthropic Claude Sonnet 4 and related catalog entries.

Set the model slug in `.env`:

```bash
INFERENCE_MODEL=anthropic-claude-sonnet-4.6
```

### Create or copy a Model Access Key

**INFERENCE** → **Serverless Inference** → **Model Access Keys** → **Create Access Key**

Export it for local runs:

```bash
export MODEL_ACCESS_KEY="your_key"
```

### Direct Serverless Inference smoke test (optional)

```bash
curl -X POST "https://inference.do-ai.run/v1/chat/completions" \
  -H "Authorization: Bearer $MODEL_ACCESS_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "anthropic-claude-sonnet-4.6",
    "messages": [{"role": "user", "content": "Reply with READY"}],
    "max_tokens": 10
  }'
```

If this fails with `401`, fix the model access key before debugging MCP.

---

## Step 6: Test in RAG Playground, tune reranking, deploy with ADK

### Validate answers in RAG Playground

RAG Playground combines retrieval plus generation in the UI. This is the fastest place to compare models before you ship agent code.

1. **INFERENCE** → **Agent Platform** → **Knowledge bases** → select your KB.
2. Open the **RAG Playground** tab.
3. Under **Instructions**, add system guidance:

```text
You assist attorneys with internal matter research.
Cite matter IDs and dates.
Do not give client-facing legal advice.
```

4. Under **Settings**, start with **Max Tokens** 800 and **Temperature** 0.1.
5. Pick **Claude Sonnet 4.6** or **Llama 3.3 Instruct 70B** from the model dropdown.
6. Ask: `What is the litigation budget for case 2024-0310?`

Review retrieved chunks under the answer. Each chunk shows source, page when available, and whether reranking ran.

RAG Playground generation bills Serverless Inference tokens. Retrieval bills Knowledge Base embedding and optional reranking tokens per [pricing](https://docs.digitalocean.com/products/inference/details/pricing/#knowledge-bases).

### Tune reranking when precision is low

If Playground pulls the wrong matter:

1. Open the knowledge base **Settings** tab.
2. Confirm reranking is enabled with your chosen reranking model.
3. Re-run the same query in **Retrieve** with and without reranking.
4. Tighten prompts with explicit matter IDs.
5. Add `item_name` filters in agent code for single-matter sessions.

Disabling reranking for one query is possible in the Control Panel per [reranking docs](https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/#test-reranking).

### Deploy without ADK (if Feature Preview is unavailable)

ADK deploy requires the **Gradient AI Agent Development Kit** feature preview on your team. If you cannot enable it, the tutorial is still complete — you already built the managed RAG stack (Spaces → Knowledge Base → retrieval → Serverless Inference). Use one of these hosting paths instead:

| Path | What you get | When to use |
| --- | --- | --- |
| **FastAPI + App Platform** (`serve.py`) | Public HTTPS `POST /run` with same JSON shape | Code-first production deploy without ADK |
| **RAG Playground** | UI for retrieval + generation on your KB | Fastest validation, no deploy |
| **Local `uvicorn`** | Same API on `localhost` | Dev and demos |
| **ADK** (`gradient agent deploy`) | Managed agent hosting + traces | When Feature Preview is enabled |

**Recommended: FastAPI service**

```bash
cd legaltech-rag-agent
pip install -r requirements-serve.txt
set -a && source .env && set +a
export RETRIEVAL_MODE=rest
uvicorn serve:app --host 0.0.0.0 --port 8080
```

`RETRIEVAL_MODE=rest` calls the [Knowledge Base retrieve API](https://docs.digitalocean.com/products/inference/how-to/test-knowledge-base-retrieval/) directly (stable in production). Use `mcp` when you want to demo the MCP tool transport locally.

Deploy to [App Platform](https://docs.digitalocean.com/products/app-platform/) with `.do/app.yaml` and `legaltech-rag-agent/Dockerfile` — no ADK flag required.

### Deploy with ADK (optional)

When local `gradient agent run` passes **and** ADK Feature Preview is enabled:

```bash
export DIGITALOCEAN_API_TOKEN="your_deploy_token"
gradient agent deploy
```

On success you receive a URL like `https://agents.do-ai.run/v1/{workspace-id}/development/run`.

### Observability

- **ADK path:** Agent Platform workspace traces show `@trace_retriever` and `@trace_llm` spans.
- **FastAPI path:** Use App Platform logs and optional application logging around `rag_core.run_rag`.
- **RAG Playground:** Inspect retrieved chunks per query in the Control Panel.

---

## Cost sketch for a solo founder (honest numbers)

These figures come from [DigitalOcean Inference pricing](https://docs.digitalocean.com/products/inference/details/pricing/). Your invoice depends on file size, query volume, and model choice.

| Line item | Example math | Notes |
| --- | --- | --- |
| Initial indexing | 10 MB corpus ≈ 3M tokens × $0.009/1M ≈ $0.03 with `all-mini-lm-l6-v2` | Scales linearly with tokens |
| OpenSearch storage | Depends on cluster size | See [OpenSearch pricing](https://docs.digitalocean.com/products/databases/opensearch/details/pricing/) |
| Retrieval query | 1 query vectorized per MCP call | Same price through MCP or REST |
| Reranking | Per reranking tokens when enabled | `BGE Reranker v2 m3` at $0.01/1M tokens |
| Answer generation | 2K input + 500 output tokens on Sonnet 4.6 ≈ $0.0135 per answer | (($3×2) + ($15×0.5)) / 1000 |

For 10,000 files, run the indexing cost estimator in the Control Panel during knowledge base creation. The UI shows per-model token rates before you commit.

---

## When things go wrong

| Symptom | Likely cause | What to try |
| --- | --- | --- |
| MCP `401` | Token missing `GenAI:read` | Create a new token with correct scope |
| `retrieve_knowledge_base` returns 0 chunks | Indexing incomplete or wrong bucket | Check **Activity** tab, re-run indexing |
| Answers cite the wrong matter | Hybrid search too broad | Lower temperature, add `item_name` filter, enable reranking |
| `gradient agent deploy` fails with `feature not enabled` | ADK Feature Preview off for your team | Enable **ADK** on [Feature Preview](https://cloud.digitalocean.com/account/feature-preview), wait ~5 minutes, redeploy |
| `gradient agent deploy` fails (other) | Missing `genai` scopes or bad token | Fix token scopes, confirm `.env` is not in `.gradientignore` |
| KB create `400` on `max_chunk_size` | Value exceeds embedding model limit | Use `256` for All MiniLM L6 v2 (not `500`) |
| Model errors on `401` | Confused API token vs model access key | Use `MODEL_ACCESS_KEY` for inference only |
| Slow first query | Cold index or large `num_results` | Start with `num_results: 5`, scale after profiling |
| Upload stalls | Batch too large | Upload fewer than 100 files per batch under 2 GB |

---

## Cleanup (so lab spend stops)

1. Destroy the agent deployment: **Agent Platform** → workspace → **Destroy agent deployment**.
2. Delete the knowledge base: **Knowledge bases** → **…** → **Destroy** (destroys associated data sources and indexing).
3. Delete the OpenSearch database if you created a dedicated one and no longer need it.
4. Delete the Spaces bucket when you no longer need raw files.
5. Revoke tutorial API tokens and model access keys.

OpenSearch clusters and stored embeddings accrue cost while resources still exist.

---

## FAQs

### 1. What is the difference between Knowledge Bases MCP and the DigitalOcean MCP server?

The [DigitalOcean MCP server](https://docs.digitalocean.com/reference/mcp/) manages DO infrastructure like Droplets, Apps, and Spaces keys. The [Knowledge Bases MCP endpoint](https://docs.digitalocean.com/reference/mcp/kbaas-mcp-tools/) at `https://kbaas.do-ai.run/v1/mcp` only exposes retrieval tools for indexed knowledge bases. You configure them separately.

### 2. Do I still need LangChain or Chroma if I use Knowledge Bases?

No Chroma or self-hosted vector DB is required for this path. You still use LangChain in agent code if you want LangChain agents, but retrieval runs on DigitalOcean managed OpenSearch through Knowledge Bases.

### 3. How does MCP billing work for retrieval?

Retrieval through MCP is billed the same as the retrieve API, including query vectorization tokens and optional reranking tokens per [Knowledge Base pricing](https://docs.digitalocean.com/products/inference/details/pricing/#knowledge-bases).

### 4. When should I enable reranking?

Enable reranking when recall looks good but ranked order is wrong, which is common when matter titles and party names overlap. You pay extra reranking tokens on each retrieval call.

### 5. Can I use Dedicated Inference instead of Serverless?

Yes for answer generation if you need a private GPU endpoint. Knowledge Base retrieval stays on the managed Knowledge Bases service. Many solo founders start on Serverless ($3.00 per 1M input tokens for Claude Sonnet 4.6) and move generation to Dedicated when traffic steadies. See [Serverless vs Dedicated](https://www.digitalocean.com/community/tutorials/serverless-vs-dedicated-vs-batch-inference).

### 6. How do I ground answers across 10,000+ files without blowing token budgets?

Keep `num_results` between 5 and 8, filter by `item_name` when the matter is known, and use reranking instead of sending 25 large chunks every call. Test prompts in RAG Playground before you ship agent defaults.

---

## What to read next

- [How to Create and Manage Knowledge Bases](https://docs.digitalocean.com/products/inference/how-to/create-manage-agent-knowledge-bases/)
- [Test Knowledge Base Retrieval (RAG Playground)](https://docs.digitalocean.com/products/inference/how-to/test-knowledge-base-retrieval/)
- [Knowledge Bases MCP Tools](https://docs.digitalocean.com/reference/mcp/kbaas-mcp-tools/)
- [Use Agent Development Kit](https://docs.digitalocean.com/products/inference/getting-started/use-adk/)
- [Build Agents Using ADK](https://docs.digitalocean.com/products/inference/how-to/build-agents-using-adk/)
- [Guide to RAG and MCP](https://www.digitalocean.com/community/tutorials/engineers-guide-rag-vs-mcp-llms)
- [Inference product docs](https://docs.digitalocean.com/products/inference/)
- [Knowledge Base retrieval best practices](https://docs.digitalocean.com/products/inference/concepts/knowledge-base-retrieval-best-practices/)

---

## Implementation notes from this session

This walkthrough was executed end-to-end on a live DigitalOcean account (June 2026). Resources created:

| Resource | Value |
| --- | --- |
| Project | `c8ab903d-17e5-4c15-bfee-7141464e3202` (Anish-tutorials-testing) |
| Spaces bucket | `legaltech-casefiles-anish` (tor1, prefix `cases/`) |
| Knowledge Base | `legaltech-cases-kb-anish` |
| Knowledge Base UUID | `0805615a-631e-11f1-b074-4e013e2ddde4` |
| Embeddings model | All MiniLM L6 v2 (`22652c2a-79ed-11ef-bf8f-4e013e2ddde4`) |
| Indexing | `INDEX_JOB_STATUS_COMPLETED`, 4/4 files, 1202 tokens |
| Inference model | `anthropic-claude-sonnet-4` |
| ADK workspace | `legaltech-rag-anish` / `development` |

**Verified working:** Spaces upload, KB API create, REST retrieve, MCP `retrieve_knowledge_base`, local `gradient agent run` with full RAG answers.

**Deploy blocker:** `gradient agent deploy` returns `permission denied: feature not enabled for this team` until **ADK Feature Preview** is enabled at [Feature Preview](https://cloud.digitalocean.com/account/feature-preview). After enabling, wait up to five minutes and rerun deploy from `legaltech-rag-agent/`. The `.env` file must ship with the deployment package (do not list `.env` in `.gradientignore`).

---

## One-command pipeline (after config.env is filled)

```bash
source config.env
./scripts/run_all.sh
```

This runs upload, Knowledge Base creation, indexing wait, REST retrieval test, and MCP retrieval test in order. Use it after you complete Step 0.
