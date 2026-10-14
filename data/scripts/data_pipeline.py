"""Build the four index datasets in data/processed/ from the SEED table.

Sizes and dates follow public shrinkflation reports. Prices are representative,
not quotes. See data/README.md.
"""

import hashlib
import json
import os
from collections import defaultdict

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "processed")

# (product_id, name, brand, category, subcategory, unit,
#  old_size, new_size, old_price, new_price, date_changed, source, retailer)
# Rows where new_size == old_size are control products that never shrank.
# fmt: off
SEED = [
    # --- Snacks (Frito-Lay / PepsiCo) ---
    ("doritos-nacho-001", "Doritos Nacho Cheese Tortilla Chips", "Frito-Lay", "Snacks", "Chips", "oz", 9.75, 9.25, 4.99, 4.99, "2022-03-15", "FullCarts.org", "Kroger"),
    ("lays-classic-001", "Lay's Classic Potato Chips Party Size", "Frito-Lay", "Snacks", "Chips", "oz", 13.0, 12.5, 5.99, 5.99, "2022-08-01", "FullCarts.org", "Kroger"),
    ("tostitos-scoops-001", "Tostitos Scoops Tortilla Chips", "Frito-Lay", "Snacks", "Chips", "oz", 10.0, 9.25, 4.79, 4.99, "2023-01-20", "ShrinkWatch.app", "Kroger"),
    ("cheetos-crunchy-001", "Cheetos Crunchy Cheese Snacks", "Frito-Lay", "Snacks", "Chips", "oz", 8.5, 8.0, 4.49, 4.49, "2023-05-10", "r/shrinkflation", "Walmart"),
    ("fritos-original-001", "Fritos Original Corn Chips", "Frito-Lay", "Snacks", "Chips", "oz", 9.75, 9.25, 4.29, 4.29, "2022-11-05", "FullCarts.org", "Kroger"),
    ("smartfood-popcorn-001", "Smartfood White Cheddar Popcorn", "Frito-Lay", "Snacks", "Popcorn", "oz", 6.75, 6.75, 4.19, 4.19, "2024-01-01", "catalog", "Kroger"),
    ("ritz-original-001", "Ritz Original Crackers Family Size", "Mondelez", "Snacks", "Crackers", "oz", 20.5, 17.8, 5.49, 5.49, "2023-03-12", "Mouseprint.org", "Walmart"),
    ("wheat-thins-001", "Wheat Thins Original Family Size", "Mondelez", "Snacks", "Crackers", "oz", 16.0, 14.0, 5.29, 5.29, "2022-09-18", "FullCarts.org", "Target"),

    # --- Candy / Sweets ---
    ("cadbury-dairymilk-001", "Cadbury Dairy Milk Sharing Bar", "Mondelez", "Candy", "Chocolate", "oz", 6.38, 5.32, 3.99, 3.99, "2023-02-01", "Capital One Shopping", "Kroger"),
    ("hersheys-kisses-001", "Hershey's Kisses Family Bag", "Hershey", "Candy", "Chocolate", "oz", 18.0, 16.9, 7.49, 7.49, "2023-07-22", "FullCarts.org", "Walmart"),
    ("mms-peanut-001", "M&M's Peanut Sharing Size", "Mars", "Candy", "Chocolate", "oz", 10.7, 10.05, 5.29, 5.49, "2023-10-04", "ShrinkSpotter.com", "Kroger"),
    ("haribo-goldbears-001", "Haribo Goldbears Gummi Candy", "Haribo", "Candy", "Gummies", "oz", 5.0, 4.0, 1.99, 1.99, "2022-06-14", "r/shrinkflation", "Walgreens"),

    # --- Cereal / Breakfast ---
    ("cocoa-puffs-fam-001", "Cocoa Puffs Family Size Cereal", "General Mills", "Cereal", "Kids Cereal", "oz", 19.3, 18.1, 5.99, 5.99, "2022-04-25", "Capital One Shopping", "Kroger"),
    ("cinn-toast-crunch-001", "Cinnamon Toast Crunch Family Size", "General Mills", "Cereal", "Kids Cereal", "oz", 19.3, 18.8, 5.99, 6.29, "2022-05-02", "Mouseprint.org", "Target"),
    ("frosted-flakes-001", "Kellogg's Frosted Flakes Giant Size", "Kellogg's", "Cereal", "Kids Cereal", "oz", 26.8, 24.0, 7.29, 7.29, "2023-04-11", "FullCarts.org", "Walmart"),
    ("quaker-oats-001", "Quaker Old Fashioned Oats", "PepsiCo", "Cereal", "Oats", "oz", 42.0, 42.0, 6.49, 6.49, "2024-01-01", "catalog", "Kroger"),
    ("eggo-waffles-001", "Eggo Homestyle Waffles", "Kellogg's", "Cereal", "Frozen Breakfast", "count", 10.0, 8.0, 3.49, 3.49, "2023-08-30", "r/shrinkflation", "Kroger"),

    # --- Household (P&G / others) ---
    ("charmin-ultrasoft-001", "Charmin Ultra Soft Mega Roll 12-pack (sheets/roll)", "Procter & Gamble", "Household", "Toilet Paper", "sheets", 264.0, 244.0, 13.99, 13.99, "2022-02-10", "Mouseprint.org", "Kroger"),
    ("bounty-select-001", "Bounty Select-A-Size Double Roll (sheets/roll)", "Procter & Gamble", "Household", "Paper Towels", "sheets", 98.0, 90.0, 10.99, 10.99, "2022-12-01", "FullCarts.org", "Walmart"),
    ("tide-pods-001", "Tide PODS Original 3-in-1", "Procter & Gamble", "Household", "Laundry", "count", 81.0, 76.0, 21.99, 21.99, "2023-06-15", "ShrinkWatch.app", "Target"),
    ("dawn-ultra-001", "Dawn Ultra Dishwashing Liquid", "Procter & Gamble", "Household", "Dish Soap", "fl oz", 7.0, 6.5, 1.79, 1.79, "2023-09-08", "Mouseprint.org", "Kroger"),
    ("gain-detergent-001", "Gain Liquid Laundry Detergent", "Procter & Gamble", "Household", "Laundry", "fl oz", 88.0, 73.0, 11.99, 11.99, "2022-07-19", "Capital One Shopping", "Walmart"),
    ("kleenex-ultra-001", "Kleenex Ultra Soft Facial Tissues (per box)", "Kimberly-Clark", "Household", "Facial Tissue", "count", 65.0, 60.0, 2.19, 2.19, "2022-10-26", "FullCarts.org", "Kroger"),
    ("hefty-bags-001", "Hefty Strong Tall Kitchen Bags", "Reynolds", "Household", "Trash Bags", "count", 90.0, 90.0, 13.49, 13.49, "2024-01-01", "catalog", "Kroger"),

    # --- Beverages ---
    ("gatorade-tq-001", "Gatorade Thirst Quencher Fruit Punch", "PepsiCo", "Beverages", "Sports Drinks", "fl oz", 32.0, 28.0, 1.99, 1.99, "2021-12-06", "Capital One Shopping", "Kroger"),
    ("tropicana-oj-001", "Tropicana Pure Premium Orange Juice", "PepsiCo", "Beverages", "Juice", "fl oz", 59.0, 52.0, 4.39, 4.39, "2022-01-17", "Mouseprint.org", "Kroger"),
    ("folgers-classic-001", "Folgers Classic Roast Ground Coffee", "J.M. Smucker", "Beverages", "Coffee", "oz", 51.0, 43.5, 12.99, 12.99, "2021-11-08", "Mouseprint.org", "Walmart"),
    ("coke-12pk-001", "Coca-Cola Classic 12-pack Cans", "Coca-Cola", "Beverages", "Soda", "fl oz", 144.0, 144.0, 7.99, 7.99, "2024-01-01", "catalog", "Kroger"),

    # --- Personal Care ---
    ("crest-3d-001", "Crest 3D White Toothpaste", "Procter & Gamble", "Personal Care", "Oral Care", "oz", 4.1, 3.8, 4.49, 4.49, "2023-03-27", "ShrinkSpotter.com", "Walgreens"),
    ("pantene-shampoo-001", "Pantene Pro-V Daily Moisture Shampoo", "Procter & Gamble", "Personal Care", "Hair Care", "fl oz", 12.6, 10.4, 5.99, 5.99, "2022-05-23", "FullCarts.org", "Target"),
    ("dove-bodywash-001", "Dove Deep Moisture Body Wash", "Unilever", "Personal Care", "Body Wash", "fl oz", 24.0, 22.0, 7.99, 7.99, "2023-11-13", "r/shrinkflation", "Kroger"),

    # --- Frozen / Dairy ---
    ("tillamook-ice-001", "Tillamook Old-Fashioned Vanilla Ice Cream", "Tillamook", "Frozen & Dairy", "Ice Cream", "fl oz", 56.0, 48.0, 6.49, 6.49, "2021-09-20", "Mouseprint.org", "Kroger"),
    ("breyers-natural-001", "Breyers Natural Vanilla", "Unilever", "Frozen & Dairy", "Ice Cream", "fl oz", 48.0, 48.0, 5.49, 5.49, "2024-01-01", "catalog", "Kroger"),
    ("chobani-flip-001", "Chobani Flip Greek Yogurt", "Chobani", "Frozen & Dairy", "Yogurt", "oz", 5.3, 4.5, 1.79, 1.79, "2023-12-04", "r/shrinkflation", "Kroger"),
]
# fmt: on


def shrinkage_pct(old_size, new_size):
    """Percent of the package that disappeared (0.0 if it did not shrink)."""
    if new_size >= old_size:
        return 0.0
    return round((old_size - new_size) / old_size * 100, 1)


def price_per_unit(price, size):
    return round(price / size, 4)


def effective_price_increase_pct(old_price, old_size, new_price, new_size):
    """Percent change in price-per-unit — the increase shrinkflation hides."""
    old_ppu = price_per_unit(old_price, old_size)
    new_ppu = price_per_unit(new_price, new_size)
    return round((new_ppu - old_ppu) / old_ppu * 100, 1)


def severity(shrink_pct):
    if shrink_pct >= 15:
        return "high"
    if shrink_pct >= 7:
        return "medium"
    return "low"


def make_upc(product_id):
    """Stable 12-digit placeholder UPC derived from the product id.

    Uses SHA-256 rather than hash(), which is salted per process and made
    the generated dataset differ on every run.
    """
    digest = int(hashlib.sha256(product_id.encode("utf-8")).hexdigest(), 16)
    return f"0{digest % 10**11:011d}"


def year_before(date_str, years=1):
    y, rest = date_str.split("-", 1)
    return f"{int(y) - years}-{rest}"


def year_after(date_str, years=1):
    y, rest = date_str.split("-", 1)
    return f"{int(y) + years}-{rest}"


def build_datasets():
    """Return {filename: records} for the four index datasets."""
    products, history, alerts = [], [], []
    category_stats = defaultdict(lambda: {"total": 0, "affected": 0, "shrink": []})

    for (
        pid,
        name,
        brand,
        cat,
        subcat,
        unit,
        old_size,
        new_size,
        old_price,
        new_price,
        date_changed,
        source,
        retailer,
    ) in SEED:
        shrunk = new_size < old_size
        shrink_pct = shrinkage_pct(old_size, new_size)
        new_ppu = price_per_unit(new_price, new_size)
        eff_increase = effective_price_increase_pct(old_price, old_size, new_price, new_size)

        products.append(
            {
                "product_id": pid,
                "name": name,
                "brand": brand,
                "category": cat,
                "subcategory": subcat,
                "upc": make_upc(pid),
                "current_size": new_size,
                "current_size_unit": unit,
                "current_price": new_price,
                "price_per_unit": new_ppu,
                "description": f"{name} sold at {retailer}. Category: {cat} / {subcat}.",
                "retailer": retailer,
                "last_updated": "2026-06-01",
                "shrinkflation_flag": shrunk,
            }
        )

        # Only the change itself is documented. The points around it are
        # interpolated, with a little price drift so the series isn't flat.
        history_points = [
            (year_before(date_changed, 2), old_size, round(old_price * 0.96, 2)),
            (year_before(date_changed, 1), old_size, old_price),
            (date_changed, new_size, new_price),
            (year_after(date_changed, 1), new_size, round(new_price * 1.02, 2)),
            ("2026-05-15", new_size, round(new_price * 1.04, 2)),
        ]
        prev_size, prev_price = None, None
        for i, (record_date, size, price) in enumerate(history_points):
            size_chg = round((size - prev_size) / prev_size * 100, 1) if prev_size else 0.0
            price_chg = round((price - prev_price) / prev_price * 100, 1) if prev_price else 0.0
            history.append(
                {
                    "record_id": f"{pid}-h{i + 1}",
                    "product_id": pid,
                    "name": name,
                    "brand": brand,
                    "category": cat,
                    "size": size,
                    "size_unit": unit,
                    "price": price,
                    "price_per_unit": price_per_unit(price, size),
                    "record_date": record_date,
                    "source": source if record_date == date_changed else "retail price capture",
                    "retailer": retailer,
                    "size_change_pct": size_chg,
                    "price_change_pct": price_chg,
                }
            )
            prev_size, prev_price = size, price

        if shrunk:
            alerts.append(
                {
                    "alert_id": f"alert-{pid}",
                    "product_id": pid,
                    "product_name": name,
                    "brand": brand,
                    "category": cat,
                    "old_size": old_size,
                    "new_size": new_size,
                    "size_unit": unit,
                    "shrinkage_pct": shrink_pct,
                    "old_price": old_price,
                    "new_price": new_price,
                    "effective_price_increase_pct": eff_increase,
                    "date_changed": date_changed,
                    "source": source,
                    "severity": severity(shrink_pct),
                    "verified": source != "r/shrinkflation",
                }
            )

        category_stats[cat]["total"] += 1
        if shrunk:
            category_stats[cat]["affected"] += 1
            category_stats[cat]["shrink"].append(shrink_pct)

    categories = []
    for i, (cat, stats) in enumerate(sorted(category_stats.items()), 1):
        shrinks = stats["shrink"]
        avg = round(sum(shrinks) / len(shrinks), 1) if shrinks else 0.0
        categories.append(
            {
                "category_id": f"cat-{i:03d}",
                "category_name": cat,
                "avg_shrinkage_pct": avg,
                "total_products": stats["total"],
                "affected_products": stats["affected"],
                "shrinkflation_rate": round(stats["affected"] / stats["total"], 2),
            }
        )

    return {
        "products.json": products,
        "product_history.json": history,
        "shrinkflation_alerts.json": alerts,
        "categories.json": categories,
    }


def serialize(records):
    return json.dumps(records, indent=2) + "\n"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for fname, records in build_datasets().items():
        with open(os.path.join(OUT_DIR, fname), "w", encoding="utf-8", newline="\n") as f:
            f.write(serialize(records))
        print(f"wrote {fname}: {len(records)} records")


if __name__ == "__main__":
    main()
