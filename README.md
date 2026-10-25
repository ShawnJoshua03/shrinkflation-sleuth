<div align="center">

# Shrinkflation Sleuth

**A Gemini agent that checks whether a grocery product has shrunk and works out how much more you now pay per unit.**

[![CI](https://github.com/ShawnJoshua03/shrinkflation-sleuth/actions/workflows/ci.yml/badge.svg)](https://github.com/ShawnJoshua03/shrinkflation-sleuth/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?logo=javascript&logoColor=black)
![Google ADK](https://img.shields.io/badge/Google%20ADK-4285F4?logo=google&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini-8E75B2?logo=googlegemini&logoColor=white)
![Elasticsearch](https://img.shields.io/badge/Elasticsearch-005571?logo=elasticsearch&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
[![Live demo](https://img.shields.io/badge/Live%20demo-open-2ea44f)](https://shawnjoshua03.github.io/shrinkflation-sleuth/)
[![Write-up](https://img.shields.io/badge/Write--up-read-blue)](https://shawnjoshua03.github.io/stories/shrinkflation-sleuth/)

[![Sleuth Explorer: product lookup showing the Doritos size cut and +5.4% hidden price increase](https://shawnjoshua03.github.io/images/shrinkflation-sleuth.jpg)](https://shawnjoshua03.github.io/shrinkflation-sleuth/#explorer)

**[Portfolio](https://shawnjoshua03.github.io/)**

</div>

I built it for the [Google Cloud Rapid Agent Hackathon](https://rapid-agent.devpost.com/) (Elastic track) in three days, with Google ADK, Gemini, Elasticsearch and the Elastic MCP server.

Shrinkflation is when a product gets smaller and the price stays the same. It's an economic idea that has interested me for a long time. A lot of companies use it to make any tiny bit of extra profit they can, and a smaller bag at the same price is easy to miss. Capital One Shopping research estimates it has touched roughly a third of grocery items. The number that shows it is the price per ounce, so that's what this agent reports.

## How it works

The agent is one Google ADK `LlmAgent` with six playbooks written into its prompt: product lookup, brand investigation, category analysis, shopping-list audit, trend dashboard and data discovery. Gemini picks the playbook. All data access goes through five read-only Elastic MCP tools: `search`, `esql`, `list_indices`, `get_mappings` and `get_shards`.

A product lookup is three tool calls:

1. `search` the products index (fuzzy `multi_match`) to get a `product_id`.
2. `esql` over `product_history` for that id, computing price per unit at each point.
3. `search` `shrinkflation_alerts` for the documented change and its source. Reddit-only reports are marked unverified.

The answer leads with the effective price increase, meaning the change in price per unit. When the price holds, it's always larger than the shrinkage: 20% less product at the same price is 25% more per unit.

```mermaid
flowchart LR
    U([Shopper]) -->|question| A["Google ADK LlmAgent<br/>Gemini Flash<br/>6 playbooks"]
    A -->|MCP tool calls| M{{"Elastic MCP server<br/>search · esql · list_indices<br/>get_mappings · get_shards"}}
    M --> ES[("Elasticsearch<br/>products · product_history<br/>shrinkflation_alerts · categories")]
    P["data_pipeline.py<br/>curated seed table"] -->|JSON| ES
    P -->|same JSON| X["Sleuth Explorer<br/>static site, GitHub Pages"]
    A -->|sourced verdict| U
```

On Cloud Run it's two services: the official `docker.elastic.co/mcp/elasticsearch` image in HTTP mode, and this repo's FastAPI app (`main.py`), which serves the ADK chat UI and reaches MCP through `ELASTIC_MCP_URL`. Locally, with `ELASTIC_MCP_URL` unset, the agent spawns [`es_mcp_server.py`](agents/shrinkflation_sleuth/es_mcp_server.py), a small Python server with the same five tools over stdio, so you don't need Docker. Tool-by-tool details are in [docs/architecture.md](docs/architecture.md).

## The live demo

The full agent needs an Elasticsearch cluster and a Gemini key. Neither can be hosted publicly for free, and a public LLM endpoint would expose the key, so the [live demo](https://shawnjoshua03.github.io/shrinkflation-sleuth/) is a static page instead. It runs five of the six playbooks in plain JavaScript over the same JSON files the agent queries, and each panel shows the tool calls the agent would make. There's no LLM in it.

## Results

- 34 products from 16 brands in 7 categories. 29 had a documented size cut (24 verified), and 5 are unchanged controls.
- Across the 29 cuts, price per unit went up 12.2% on average, from an average shrinkage of 10.2%.
- Worst case: Haribo Goldbears went from 5 oz to 4 oz at the same $1.99, a 25% increase per ounce.
- By category (verified events only), Frozen & Dairy averages 14.3% shrinkage, but that's a single event. Beverages is next at 13.0% across 3.

## Limitations

- I never measured the agent's answers. I spot-checked the six query types by hand. There's no eval of answer quality or tool-call accuracy.
- The data is small and partly synthetic. Sizes, dates and sources come from public reports. Prices are representative, and the history points around each change are interpolated. See [data/README.md](data/README.md).
- The prompt hardcodes the four index names and their fields, so a different schema means editing the prompt.
- The Elastic Cloud cluster from the hackathon is shut down. To run the agent, load the data into your own cluster with `make index`.
- The explorer's search imitates Elasticsearch's `multi_match` with `fuzziness: AUTO`. It isn't Elasticsearch, so some queries rank differently.
- The Cloud Run deploy uses `--allow-unauthenticated` and the app allows any CORS origin. That was fine for a hackathon demo. Put auth in front of it before running it anywhere real.

## Setup

The demo needs no accounts:

```bash
git clone https://github.com/ShawnJoshua03/shrinkflation-sleuth && cd shrinkflation-sleuth
make setup        # venv + dependencies
make serve        # http://localhost:8080
```

The full agent needs Python 3.11+, an Elasticsearch cluster (an Elastic Cloud trial or a local Docker node), and Gemini through Vertex AI or an AI Studio key:

```bash
cp .env.example .env    # fill in ES_URL, ES_API_KEY and Gemini settings
make index              # create the 4 indices and load the data
make agent              # ADK chat UI at http://localhost:8000, pick "shrinkflation_sleuth"
```

Then ask things like *"Has my Doritos bag gotten smaller?"*, *"Show me all shrinkflation from Procter & Gamble"* or *"Check these: Tide, Charmin, Folgers"*.

`make test` and `make lint` run the checks. `make data` regenerates the datasets. On Windows, run `make` from Git Bash or run the [Makefile](Makefile) commands directly.

To deploy to Cloud Run (needs a GCP billing account), deploy the MCP server first, then the agent:

```bash
gcloud run deploy elastic-mcp --image=docker.elastic.co/mcp/elasticsearch \
  --args=http --port=8080 --region=us-central1 --set-env-vars=ES_URL=...,ES_API_KEY=...
gcloud builds submit --config cloudbuild.yaml   # expects es-url / es-api-key / elastic-mcp-url in Secret Manager
```

## Decisions

I used one agent with playbooks instead of a pipeline of agents. A fixed `SequentialAgent` (lookup, analyze, report) would push every question through a product lookup, which doesn't fit "which category is worst?" or "what data do you have?". With one `LlmAgent` there are no hand-offs between agents, and the tool sequence still shows up in the ADK trace.

Most of the agent's behaviour comes from the prompt. Each playbook step needs the previous step's output: the `product_id` from `search` feeds both the ES|QL query and the alert lookup. The prompt also says what to do when things go wrong. Zero hits get a suggestion to try a brand or category. A product with no history falls back to the alerts index. An ES|QL syntax error gets one retry with a simpler query.

ES|QL handles the analytics. One `STATS ... BY category` call replaces several aggregation round trips, which keeps the plans short.

MCP keeps the data layer swappable. In production the agent talks to the official Elastic MCP image over HTTP, and locally it talks to the Python server over stdio. Only the connection settings change.

A bug I fixed after the hackathon: the pipeline was meant to be deterministic, but it derived UPCs from Python's `hash()`, which is salted per process, so every run rewrote `products.json`. It uses SHA-256 now, and a test regenerates the data and fails if the committed files drift.

## Disclaimer

Informational only, not purchasing advice. Prices are illustrative. Product and brand names belong to their owners and appear only to describe publicly reported size changes. Not affiliated with any brand, retailer, Google or Elastic.

## License

[Apache 2.0](LICENSE)
