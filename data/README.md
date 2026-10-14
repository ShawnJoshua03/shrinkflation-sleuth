# Data

`data/processed/` holds the four JSON files loaded into Elasticsearch:

| File | Records | Contents |
|---|---|---|
| `products.json` | 34 | Current catalog: 16 brands, 7 categories |
| `product_history.json` | 170 | Five size/price points per product, 2019 to 2026 |
| `shrinkflation_alerts.json` | 29 | Documented size cuts: old and new size, shrinkage %, effective price increase %, severity, source |
| `categories.json` | 7 | Per-category average shrinkage and share of products that shrank |

`data/scripts/data_pipeline.py` builds all four from a 34-row seed table (`make data`). The output is deterministic, and a test fails if the committed files drift from it. The static explorer reads the same files.

## Sources

Size changes come from public shrinkflation reports: FullCarts.org, ShrinkWatch.app, ShrinkSpotter.com, Mouseprint.org, Capital One Shopping research (2025) and r/shrinkflation. The 5 alerts sourced only from Reddit are marked `verified: false`. The 5 rows with source `catalog` are control products that didn't shrink.

The BLS [R-CPI-SC](https://www.bls.gov/cpi/research-series/r-cpi-sc.htm) downsizing series was background only. No row comes from it.

## Caveats

- Prices are representative retail prices around the time of each change, not quotes.
- Only the change itself is documented. The other four history points per product are interpolated: the old size one and two years earlier (the earlier one 4% cheaper), then the new size a year later (+2%) and in May 2026 (+4%).
- UPCs are placeholders hashed from the product id, not real codes.

## Rebuilding

```bash
python data/scripts/data_pipeline.py
python data/scripts/create_indices.py --recreate
python data/scripts/bulk_index.py
```
