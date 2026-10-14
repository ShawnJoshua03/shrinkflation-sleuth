# Devpost submission

> The hackathon write-up, edited for style since. Two things have changed: Gemini 2.0 Flash was retired, and the Elastic Cloud deployment is offline. The main README has the current state.

**Project:** Shrinkflation Sleuth
**Tagline:** An agent that checks whether a grocery product has shrunk
**Track:** Elastic
**Built with:** Google ADK, Gemini 2.0 Flash, Elasticsearch, Elastic MCP Server, Cloud Run, Python

## Inspiration

I spent my internship at Kroger walking grocery aisles, and I kept seeing what shoppers tell researchers they see: packages getting smaller while the price stays put. Shrinkflation has affected roughly a third of grocery items and drove between 3.3% and 10.3% of grocery price inflation from 2019 to 2023. I couldn't find a mainstream tool where a shopper can ask "has my product shrunk?", so I built one.

## What it does

You ask about a product. The agent searches an Elasticsearch catalog, pulls the size and price history, computes the change in price per unit, checks it against a database of documented size cuts, and answers with a severity rating and a source. It also handles brand scorecards, category rankings, shopping-list audits, trend dashboards and questions about the data itself. Each of the six query types has its own sequence of tool calls.

## How I built it

The agent is a Google ADK `LlmAgent` running `gemini-2.0-flash`, with six playbooks in its prompt. All data access goes through the official Elastic MCP server and its five read-only tools: `search` for fuzzy product lookups, `esql` for price-per-unit math and `STATS` aggregations, `list_indices` and `get_mappings` for questions about the data, and `get_shards` for health checks.

The dataset has 34 products, 170 history records and 29 documented size cuts, curated from FullCarts, ShrinkWatch, Mouseprint and Capital One Shopping research. A pipeline script generates it and a second script bulk-indexes it into Elastic Cloud. It runs as two Cloud Run services: the Elastic MCP server in HTTP mode and the agent's FastAPI app.

## Challenges

Getting real multi-step behaviour took playbooks where each step needs the last one's output: the `product_id` from the first search is required by the ES|QL query and the alert lookup. ES|QL syntax is also strict, so the prompt tells the agent to retry once with a simpler query before reporting an error.

## What went well

Each of the five MCP tools has a job in at least one playbook. The effective price increase turns "this bag seems smaller" into a percentage with a source.

## What I learned

ES|QL fits agent analytics well: one call replaces several aggregation round trips. And most of the agent's quality came from the prompt, not the architecture.

## What's next

Live data from Open Food Facts / Open Prices or retailer APIs, user-submitted reports with photos, and alerts when a tracked product's size changes.
