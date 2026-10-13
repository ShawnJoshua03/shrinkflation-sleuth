# Data sources & methodology

## What's in here

`data/processed/` holds the four JSON datasets loaded into Elasticsearch:

- **products.json** — 34 current catalog entries (16 brands, 7 categories)
- **product_history.json** — 170 historical size/price records, ~5 per product, spanning 2019–2026, including the size-change event for each shrunk product
- **shrinkflation_alerts.json** — 29 documented shrinkflation events with old/new sizes, computed shrinkage %, effective price-increase %, severity, and source attribution
- **categories.json** — 7 category rollups (avg shrinkage, shrinkflation rate)

All four are generated deterministically by `data/scripts/data_pipeline.py` from a curated seed table (`make data`); a test fails if the committed files drift from the pipeline output. The same files are served to the static Sleuth Explorer demo.

## Sources

Size-change events were curated from publicly documented shrinkflation reports:

1. **FullCarts.org** — community-verified shrinkflation database (2,100+ events)
2. **ShrinkWatch.app / ShrinkSpotter.com** — confirmed products with old/new sizes
3. **Mouseprint.org** — consumer-advocacy reporting on package downsizing
4. **Capital One Shopping research (2025)** — category-level statistics and specific documented examples
5. **BLS R-CPI-SC** (https://www.bls.gov/cpi/research-series/r-cpi-sc.htm) — official downsizing-frequency context by category
6. **r/shrinkflation** — anecdotal photo evidence; entries sourced *only* from Reddit are marked `verified: false`

## Caveats

- Prices are representative retail prices at the time of the documented change, not a live feed. Price-per-unit math and shrinkage percentages are computed from the recorded sizes/prices.
- History records between documented events are interpolated at the recorded size with small price drift, to give the agent a realistic time series to query.
- This is a demo-scale dataset built for a 3-day hackathon. UPCs are deterministic placeholders, not real product codes; the pipeline is designed so larger feeds (Open Food Facts / Open Prices, retailer APIs) can be dropped into the same schema.

## Rebuilding

```bash
python data/scripts/data_pipeline.py     # regenerate processed JSON
python data/scripts/create_indices.py --recreate
python data/scripts/bulk_index.py
```
