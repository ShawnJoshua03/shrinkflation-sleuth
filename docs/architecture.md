# Architecture

## Components

| Layer | Choice | Why |
|---|---|---|
| Reasoning | Gemini Flash (`GEMINI_MODEL`, default `gemini-2.5-flash`; `gemini-2.0-flash` at the hackathon) | Hackathon requirement; fast multi-step tool use |
| Agent framework | Google ADK `LlmAgent` | Code-first control, runnable locally (`adk web`) and deployable to Cloud Run via `get_fast_api_app` |
| Data layer | Elasticsearch (Elastic Cloud) | Full-text product search + ES\|QL analytics in one engine |
| Integration | Official Elastic MCP server (Cloud Run) / `es_mcp_server.py` (local) | The same five read-only tools exposed over MCP: HTTP on Cloud Run, stdio locally |

## Why a single orchestrating LlmAgent

The build plan considered a `SequentialAgent` pipeline (lookup → analyze → report). That forces every query through a product lookup, which is wrong for category/brand/discovery queries. Instead, one `LlmAgent` carries six explicit playbooks in its instruction and lets Gemini select the right tool sequence per query type. Fewer moving parts, no agent-transfer failure modes, and the multi-step behavior is still fully visible in the trace.

## Meaningful use of all five Elastic MCP tools

| Tool | When | Why it matters |
|---|---|---|
| `search` | product lookups, brand filters, alert retrieval | fuzzy `multi_match` over name/brand/description — Elasticsearch's core strength |
| `esql` | price-per-unit EVALs, `STATS` aggregations by brand/category/year | the analytical engine behind every verdict and ranking |
| `list_indices` | data-discovery queries, first-run orientation | the agent discovers its data dynamically, nothing hardcoded |
| `get_mappings` | schema summaries during discovery | schema-aware querying instead of guessed field names |
| `get_shards` | data health/status questions | production-readiness awareness |

## Request flow (product lookup)

1. `search` products — `multi_match` on `name^3, brand^2, description`, `fuzziness: AUTO` → `product_id`
2. `esql` — `FROM product_history | WHERE product_id == "<id>" | EVAL ppu = price / size | SORT record_date ASC`
3. `search` shrinkflation_alerts by `product_id` → verified event + source
4. Gemini synthesizes: size change, effective price increase, severity (🟢🟡🔴), consumer tip, one suggested follow-up

## Deployment topology (Cloud Run)

Two services: `elastic-mcp` (official image in HTTP mode, holds ES credentials) and `shrinkflation-sleuth` (this repo's container; FastAPI app serving the ADK chat UI and API). The agent reaches the MCP service via `ELASTIC_MCP_URL`. Locally, with `ELASTIC_MCP_URL` unset, the agent spawns `agents/shrinkflation_sleuth/es_mcp_server.py` over stdio. It is a small FastMCP server that wraps the Elasticsearch Python client and exposes the same five tools, so no Docker is needed.


