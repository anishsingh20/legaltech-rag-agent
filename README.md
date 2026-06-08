# Setup runbook: Knowledge Base + MCP + ADK

Follow these steps in order. Every command assumes you are in the `Zero-Infrastructure RAG Agent/` folder.

## Before you start

1. Create a [DigitalOcean API token](https://cloud.digitalocean.com/account/api/tokens) with:
   - `genai` create, read, update, delete
   - `GenAI:read` (for retrieval and MCP)
   - `project` read
2. Create a **Model Access Key** under **INFERENCE → Serverless Inference → Model Access Keys**.
3. Create a **Spaces access key** (Control Panel or DigitalOcean MCP `spaces-key-create`).
4. Optional: enable **ADK Feature Preview** on the [Feature Preview page](https://cloud.digitalocean.com/account/feature-preview) for `gradient agent deploy`. If unavailable, use **FastAPI** (`serve.py`) or **RAG Playground** instead (see Step I).

## Quick start (automated path)

```bash
cd "Zero-Infrastructure RAG Agent"

# 1. Configure secrets
cp config.env.example config.env
# Edit config.env with your tokens and DO_PROJECT_ID

# 2. Install upload dependency
pip install -r scripts/requirements.txt

# 3. Discover IDs (prints project UUID, embedding models, VPC)
source config.env
chmod +x scripts/*.sh legaltech-rag-agent/test_mcp_retrieval.sh
./scripts/01_discover_prerequisites.sh

# 4. Put DO_PROJECT_ID into config.env, then run the full pipeline
./scripts/run_all.sh
```

`run_all.sh` executes:

| Order | Script | What it does |
| --- | --- | --- |
| 1 | `01_discover_prerequisites.py` | Lists project UUID, embedding models, VPCs, existing KBs |
| 2 | `02_upload_to_spaces.py` | Uploads `sample-case-files/*.md` to your Spaces bucket |
| 3 | `03_create_knowledge_base.py` | Creates the Knowledge Base via API and saves `KNOWLEDGE_BASE_ID` |
| 4 | `04_wait_for_indexing.py` | Polls until the KB is ready |
| 5 | `05_test_retrieve_api.sh` | Tests REST retrieval |
| 6 | `legaltech-rag-agent/test_mcp_retrieval.sh` | Tests MCP `retrieve_knowledge_base` |

## Run step by step (recommended while learning)

### Step A: Configure environment

```bash
cp config.env.example config.env
```

Open `config.env` and set at minimum:

- `DIGITALOCEAN_API_TOKEN`
- `DO_PROJECT_ID` (from step B output)
- `SPACES_ACCESS_KEY_ID`
- `SPACES_SECRET_ACCESS_KEY`
- `MODEL_ACCESS_KEY`

### Step B: Discover prerequisites

```bash
source config.env
./scripts/01_discover_prerequisites.sh
```

Copy your default project UUID into `DO_PROJECT_ID` in `config.env`.

Default values already in `config.env.example` (verified via DigitalOcean MCP during tutorial prep):

| Variable | Value | Notes |
| --- | --- | --- |
| `EMBEDDING_MODEL_UUID` | `22652c2a-79ed-11ef-bf8f-4e013e2ddde4` | All MiniLM L6 v2 |
| `VPC_UUID` | `db9169a0-e935-4329-9add-3ee52359105a` | default-tor1 |
| `KB_REGION` | `tor1` | Agent Platform default |

### Step C: Upload case files to Spaces

```bash
pip install -r scripts/requirements.txt
source config.env
python3 scripts/02_upload_to_spaces.py
```

Expected output ends with four `uploaded cases/...md` lines.

### Step D: Create the Knowledge Base (API)

```bash
source config.env
python3 scripts/03_create_knowledge_base.py
```

Expected output:

```text
Knowledge base created.
  ID:     <uuid>
  Name:   legaltech-cases-kb
  Status: provisioning
```

The script writes `KNOWLEDGE_BASE_ID` into `config.env`.

### Step E: Wait for indexing

```bash
source config.env
python3 scripts/04_wait_for_indexing.py
```

Provisioning often takes five minutes or longer. The script polls every 30 seconds.

### Step F: Test REST retrieval

```bash
source config.env
./scripts/05_test_retrieve_api.sh
```

Pass a custom query:

```bash
./scripts/05_test_retrieve_api.sh "What is the litigation budget for case 2024-0310?"
```

### Step G: Test MCP retrieval

```bash
source config.env
./legaltech-rag-agent/test_mcp_retrieval.sh
```

### Step H: Run the ADK agent locally

```bash
cd legaltech-rag-agent
cp .env.example .env
# Copy KNOWLEDGE_BASE_ID, MODEL_ACCESS_KEY, DIGITALOCEAN_API_TOKEN from config.env into .env

pip install -r requirements.txt
export $(grep -v '^#' .env | xargs)
gradient agent run
```

Test:

```bash
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Summarize case 2023-0891 and list the next deposition date."}'
```

### Step I: Run or deploy the agent (choose one path)

The RAG pipeline (Knowledge Base + Serverless Inference) does **not** require ADK. ADK is only one hosting option.

#### Path A — FastAPI service (recommended if ADK preview is unavailable)

Uses the same `POST /run` API shape. Default retrieval is **REST** (stable in production). Set `RETRIEVAL_MODE=mcp` to use MCP locally.

```bash
cd legaltech-rag-agent
pip install -r requirements-serve.txt
set -a && source .env && set +a
export RETRIEVAL_MODE=rest
uvicorn serve:app --host 0.0.0.0 --port 8080
```

Test:

```bash
curl -X POST http://localhost:8080/run \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What is the status of case 2024-0142?"}'
```

**Deploy to App Platform:** Edit `.do/app.yaml` with your secrets and `KNOWLEDGE_BASE_ID`, then:

```bash
doctl apps create --spec .do/app.yaml --project-id "$DO_PROJECT_ID"
```

The spec builds from `legaltech-rag-agent/Dockerfile` (no ADK feature preview required).

#### Path B — Agent Platform RAG Playground (no custom code)

1. **INFERENCE** → **Agent Platform** → **Knowledge bases** → your KB.
2. Open **RAG Playground**, attach your model, and test queries interactively.

This validates retrieval + generation without deploying Python.

#### Path C — Gradient ADK (optional, requires Feature Preview)

Enable **ADK Feature Preview** on the [Feature Preview page](https://cloud.digitalocean.com/account/feature-preview). If the toggle is greyed out or cannot be enabled for your team, use Path A or B instead.

```bash
cd legaltech-rag-agent
source ../.venv/bin/activate
set -a && source .env && set +a
export RETRIEVAL_MODE=mcp
gradient agent run    # local
gradient agent deploy # hosted (needs feature preview)
```

## Control Panel alternative (Step D only)

If you prefer the UI for Knowledge Base creation, skip `03_create_knowledge_base.py` and follow **Step 2B** in the main tutorial. You still run Steps C (upload) and E through G afterward.

## Cleanup

```bash
source config.env
curl -X DELETE \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/knowledge_bases/$KNOWLEDGE_BASE_ID"
```

Then delete the Spaces bucket and OpenSearch database if you created a dedicated one.
