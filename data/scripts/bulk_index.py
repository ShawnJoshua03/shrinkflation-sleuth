"""Load data/processed/*.json into Elasticsearch. Run create_indices.py first."""

import json
import os
import sys

from dotenv import load_dotenv
from elasticsearch import Elasticsearch, helpers

load_dotenv()

PROCESSED = os.path.join(os.path.dirname(__file__), "..", "processed")

DATASETS = {
    "products": ("products.json", "product_id"),
    "product_history": ("product_history.json", "record_id"),
    "shrinkflation_alerts": ("shrinkflation_alerts.json", "alert_id"),
    "categories": ("categories.json", "category_id"),
}


def actions(index, filename, id_field):
    with open(os.path.join(PROCESSED, filename)) as f:
        for doc in json.load(f):
            yield {"_index": index, "_id": doc[id_field], "_source": doc}


def main():
    es_url = os.environ.get("ES_URL")
    api_key = os.environ.get("ES_API_KEY")
    if not es_url or not api_key:
        sys.exit("Set ES_URL and ES_API_KEY (see .env.example)")

    es = Elasticsearch(es_url, api_key=api_key)

    for index, (filename, id_field) in DATASETS.items():
        ok, errors = helpers.bulk(es, actions(index, filename, id_field))
        print(f"{index}: indexed {ok} docs" + (f", {len(errors)} errors" if errors else ""))

    es.indices.refresh(index=",".join(DATASETS))
    for index in DATASETS:
        count = es.count(index=index)["count"]
        print(f"verify {index}: {count} documents")


if __name__ == "__main__":
    main()
