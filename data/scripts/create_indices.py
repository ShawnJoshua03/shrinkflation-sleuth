"""
create_indices.py — Create the four Shrinkflation Sleuth indices in
Elasticsearch with explicit mappings.

Env vars required (see .env.example):
    ES_URL      e.g. https://my-deployment.es.us-central1.gcp.cloud.es.io
    ES_API_KEY  Elasticsearch API key

Usage:
    python data/scripts/create_indices.py [--recreate]
"""

import os
import sys

from dotenv import load_dotenv
from elasticsearch import Elasticsearch

load_dotenv()

MAPPINGS = {
    "products": {
        "properties": {
            "product_id": {"type": "keyword"},
            "name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "brand": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "category": {"type": "keyword"},
            "subcategory": {"type": "keyword"},
            "upc": {"type": "keyword"},
            "current_size": {"type": "float"},
            "current_size_unit": {"type": "keyword"},
            "current_price": {"type": "float"},
            "price_per_unit": {"type": "float"},
            "description": {"type": "text"},
            "image_url": {"type": "keyword"},
            "retailer": {"type": "keyword"},
            "last_updated": {"type": "date"},
            "shrinkflation_flag": {"type": "boolean"},
        }
    },
    "product_history": {
        "properties": {
            "record_id": {"type": "keyword"},
            "product_id": {"type": "keyword"},
            "name": {"type": "text"},
            "brand": {"type": "keyword"},
            "category": {"type": "keyword"},
            "size": {"type": "float"},
            "size_unit": {"type": "keyword"},
            "price": {"type": "float"},
            "price_per_unit": {"type": "float"},
            "record_date": {"type": "date"},
            "source": {"type": "keyword"},
            "retailer": {"type": "keyword"},
            "size_change_pct": {"type": "float"},
            "price_change_pct": {"type": "float"},
        }
    },
    "shrinkflation_alerts": {
        "properties": {
            "alert_id": {"type": "keyword"},
            "product_id": {"type": "keyword"},
            "product_name": {"type": "text"},
            "brand": {"type": "keyword"},
            "category": {"type": "keyword"},
            "old_size": {"type": "float"},
            "new_size": {"type": "float"},
            "size_unit": {"type": "keyword"},
            "shrinkage_pct": {"type": "float"},
            "old_price": {"type": "float"},
            "new_price": {"type": "float"},
            "effective_price_increase_pct": {"type": "float"},
            "date_detected": {"type": "date"},
            "date_changed": {"type": "date"},
            "source": {"type": "keyword"},
            "severity": {"type": "keyword"},
            "verified": {"type": "boolean"},
        }
    },
    "categories": {
        "properties": {
            "category_id": {"type": "keyword"},
            "category_name": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "parent_category": {"type": "keyword"},
            "avg_shrinkage_pct": {"type": "float"},
            "total_products": {"type": "integer"},
            "affected_products": {"type": "integer"},
            "shrinkflation_rate": {"type": "float"},
        }
    },
}


def main():
    es_url = os.environ.get("ES_URL")
    api_key = os.environ.get("ES_API_KEY")
    if not es_url or not api_key:
        sys.exit("Set ES_URL and ES_API_KEY (see .env.example)")

    es = Elasticsearch(es_url, api_key=api_key)
    recreate = "--recreate" in sys.argv

    for index, mapping in MAPPINGS.items():
        if es.indices.exists(index=index):
            if recreate:
                es.indices.delete(index=index)
                print(f"deleted {index}")
            else:
                print(f"{index} already exists (use --recreate to rebuild)")
                continue
        es.indices.create(index=index, mappings=mapping)
        print(f"created {index}")


if __name__ == "__main__":
    main()
