# Shrinkflation Sleuth 🔍

**An AI agent that catches companies quietly shrinking your grocery products — powered by Elasticsearch and Gemini.**

Built for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) — Elastic Track.

Shrinkflation is when companies reduce product sizes while keeping prices the same. It has affected roughly a third of grocery items and drove a meaningful share of grocery price inflation, yet there's no mainstream tool that lets a shopper ask *"Has my product shrunk?"* Shrinkflation Sleuth is that tool: a multi-step agent that searches a product database, analyzes price-per-unit trends with ES|QL, cross-checks verified shrinkflation events, and returns a sourced consumer report.

## What it can do

| Ask | What happens |
|---|---|
| "Has my Doritos bag gotten smaller?" | `search` products → `esql` size/price history → `search` verified alerts → verdict |
| "Show me all shrinkflation from Frito-Lay" | brand scorecard via ES\|QL `STATS` aggregation, ranked by shrinkage |
| "Which category has the worst shrinkflation?" | category aggregation + top offenders |
| "Check these: Doritos, Charmin, Tide, Oreos" | shopping-list report card with total hidden cost |
| "What are the worst trends this year?" | top 10 events + year-over-year ES\|QL trend |
| "What data do you have?" | `list_indices` → `get_mappings` → counts (live data discovery) |

Every answer reports the **effective price increase** — the change in price-per-unit — because that's the number shrinkflation hides.

## Architecture

```
USER ──► Gemini 2.0 Flash (Google ADK LlmAgent)
              │  plans steps, selects tools
              ▼
      Elastic MCP Server (official, read-only)
      ├─ search        product lookups (query DSL, fuzzy multi_match)
      ├─ esql          price-per-unit analytics, aggregations, trends
      ├─ list_indices  dynamic data discovery
      ├─ get_mappings  schema-aware querying
      └─ get_shards    data health checks
              │
              ▼
      Elasticsearch (Elastic Cloud)
      ├─ products              34 docs — current catalog
      ├─ product_history       170 docs — size/price records 2019–2026
      ├─ shrinkflation_alerts  29 docs — documented events with sources
      └─ categories            7 docs — category-level stats
```

- **Model:** `gemini-2.0-flash`
- **Agent framework:** [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) — `LlmAgent` with playbook-style instructions for six query types
- **Elastic integration:** official `docker.elastic.co/mcp/elasticsearch` MCP server; all five read-only tools are used meaningfully (see `docs/architecture.md`)
- **Deployment:** Cloud Run (FastAPI app via `google.adk.cli.fast_api.get_fast_api_app`, which also serves the ADK chat UI)

## Quickstart (local)

Prereqs: Python 3.11+, Docker, an Elasticsearch cluster (Elastic Cloud free trial is fine), Google Cloud project with Vertex AI enabled (or an AI Studio API key).

```bash
git clone https://github.com/<you>/shrinkflation-sleuth && cd shrinkflation-sleuth
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # fill in ES_URL, ES_API_KEY, GCP settings

# 1. Generate the dataset, create indices, load data
python data/scripts/data_pipeline.py
python data/scripts/create_indices.py
python data/scripts/bulk_index.py

# 2. Run the agent (spawns the Elastic MCP server via Docker in stdio mode)
adk web agents/
# open http://localhost:8000, select "shrinkflation_sleuth"
```

## Deploy to Cloud Run

The agent container talks to the Elastic MCP server over HTTP, so deploy the MCP server as its own Cloud Run service first:

```bash
# 1. Elastic MCP server (HTTP mode)
gcloud run deploy elastic-mcp \
  --image=docker.elastic.co/mcp/elasticsearch \
  --args=http --port=8080 --region=us-central1 \
  --set-env-vars=ES_URL=...,ES_API_KEY=...

# 2. The agent itself
gcloud builds submit --config cloudbuild.yaml
# (cloudbuild.yaml expects es-url / es-api-key / elastic-mcp-url in Secret Manager)
```

Set `ELASTIC_MCP_URL` to the MCP service URL (e.g. `https://elastic-mcp-xxxx.run.app/mcp`). When `ELASTIC_MCP_URL` is unset, the agent falls back to spawning the MCP Docker image locally over stdio — convenient for development.

## Repository layout

```
agents/shrinkflation_sleuth/   ADK agent (root_agent + playbook instructions)
main.py                        Cloud Run entrypoint (FastAPI + ADK web UI)
data/scripts/                  data_pipeline.py · create_indices.py · bulk_index.py
data/processed/                generated JSON for the four indices
frontend/index.html            landing page
docs/                          architecture notes, Devpost submission draft
Dockerfile · cloudbuild.yaml   deployment
LICENSE                        Apache 2.0
```

## Data & methodology

The demo dataset covers 34 products across 12 brands and 7 categories, curated from publicly documented shrinkflation reports (FullCarts.org, ShrinkWatch, ShrinkSpotter, Mouseprint.org, Capital One Shopping research, r/shrinkflation) plus BLS context on downsizing frequency. Records sourced only from community reports are marked `verified: false`. See `data/README.md` for details and caveats.

## License

Apache 2.0 — see [LICENSE](LICENSE).
