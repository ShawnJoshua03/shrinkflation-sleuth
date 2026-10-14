# Architecture

The README covers the overall shape and the deployment topology. This page has the details.

## Components

| Layer | Choice | Why |
|---|---|---|
| Model | Gemini Flash (`GEMINI_MODEL`, default `gemini-2.5-flash`; `gemini-2.0-flash` at the hackathon, since retired) | Required by the hackathon |
| Agent framework | Google ADK `LlmAgent` | Runs locally with `adk web` and deploys to Cloud Run through `get_fast_api_app` |
| Data | Elasticsearch | The hackathon's Elastic track; fuzzy product search and ES\|QL aggregations in one place |
| Integration | Official Elastic MCP server on Cloud Run, `es_mcp_server.py` locally | Same five read-only tools over HTTP or stdio |

## How the agent uses each tool

| Tool | Used for |
|---|---|
| `search` | Product lookups (fuzzy `multi_match` on name, brand, description), brand filters, alert lookups |
| `esql` | Price-per-unit `EVAL`s and `STATS` by brand, category and year |
| `list_indices` | Answering "what data do you have?" |
| `get_mappings` | Summarizing fields for the same question |
| `get_shards` | Only when the user asks about data health |

The prompt names the four indices and their main fields, so the agent doesn't discover its schema. `list_indices` and `get_mappings` are there to answer the user.

## Product lookup, step by step

1. `search` products: `multi_match` on `name^3, brand^2, description`, `fuzziness: AUTO`. This gives the `product_id`.
2. `esql`: `FROM product_history | WHERE product_id == "<id>" | EVAL ppu = price / size | SORT record_date ASC`
3. `search` shrinkflation_alerts by `product_id` for the documented change and its source.
4. Gemini writes the answer: size change, effective price increase, severity (low, medium or high), a tip, and one suggested next check.
