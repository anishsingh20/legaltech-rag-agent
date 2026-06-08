# Solo Founders Legal AI Retrieval Policy

**Effective:** 2024-06-01  
**Owner:** Founding partner  
**Applies to:** Internal case research assistant

## Purpose

This policy defines how the firm's AI assistant retrieves answers from internal case files stored in DigitalOcean Knowledge Bases.

## Allowed Uses

- Summarize matter status for attorneys assigned to the matter.
- Surface procedural deadlines from indexed case files.
- Draft internal research memos with source citations.

## Prohibited Uses

- Do not use the assistant for client-facing advice without attorney review.
- Do not query across matters without explicit matter ID in the prompt.
- Do not upload client PII to non-production workspaces.

## Retrieval Settings

| Setting | Production value | Notes |
| --- | --- | --- |
| `num_results` | 5 | Raise to 8 for multi-defendant matters |
| `alpha` | 0.5 | Hybrid search default |
| Reranking | Enabled | Turn on when precision drops below 70% in evals |
| Model | Claude Sonnet 4.6 | Fallback: Llama 3.3 Instruct 70B |

## Cost Guardrails

- Indexing budget: $50/month for demo corpus under 500 MB.
- Query vectorization: billed per [Knowledge Base pricing](https://docs.digitalocean.com/products/inference/details/pricing/#knowledge-bases).
- Generation: billed per [Serverless Inference pricing](https://docs.digitalocean.com/products/inference/details/pricing/#serverless-inference).

## Incident Response

If the assistant cites a wrong matter ID, stop the session, log the prompt, and re-run retrieval with an `item_name` filter.
