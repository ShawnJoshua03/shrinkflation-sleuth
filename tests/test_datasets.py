"""Invariants for the generated datasets and their Elasticsearch mappings."""

import json

import pytest
from conftest import PROCESSED
from create_indices import MAPPINGS
from data_pipeline import SEED, build_datasets, serialize

INDEX_FILES = {
    "products": "products.json",
    "product_history": "product_history.json",
    "shrinkflation_alerts": "shrinkflation_alerts.json",
    "categories": "categories.json",
}


@pytest.fixture(scope="module")
def datasets():
    return build_datasets()


def test_build_is_deterministic():
    assert build_datasets() == build_datasets()


@pytest.mark.parametrize("fname", INDEX_FILES.values())
def test_committed_data_matches_pipeline(datasets, fname):
    """data/processed must be regenerated whenever the pipeline changes."""
    committed = (PROCESSED / fname).read_text(encoding="utf-8")
    assert committed == serialize(datasets[fname]), f"run `make data` to refresh {fname}"


def test_record_counts(datasets):
    assert len(datasets["products.json"]) == len(SEED) == 34
    assert len(datasets["product_history.json"]) == 5 * len(SEED)
    assert len(datasets["shrinkflation_alerts.json"]) == 29
    assert len(datasets["categories.json"]) == 7


@pytest.mark.parametrize("index,fname", INDEX_FILES.items())
def test_every_field_is_mapped(datasets, index, fname):
    mapped = set(MAPPINGS[index]["properties"])
    for doc in datasets[fname]:
        assert set(doc) == mapped, f"{index}: unmapped or missing fields"


def test_ids_are_unique(datasets):
    for fname, id_field in [
        ("products.json", "product_id"),
        ("product_history.json", "record_id"),
        ("shrinkflation_alerts.json", "alert_id"),
        ("categories.json", "category_id"),
    ]:
        ids = [d[id_field] for d in datasets[fname]]
        assert len(ids) == len(set(ids)), fname


def test_alerts_only_for_shrunk_products(datasets):
    shrunk = {p["product_id"] for p in datasets["products.json"] if p["shrinkflation_flag"]}
    alerted = {a["product_id"] for a in datasets["shrinkflation_alerts.json"]}
    assert shrunk == alerted
    for a in datasets["shrinkflation_alerts.json"]:
        assert a["new_size"] < a["old_size"]
        assert a["shrinkage_pct"] > 0


def test_reddit_only_reports_are_unverified(datasets):
    for a in datasets["shrinkflation_alerts.json"]:
        assert a["verified"] == (a["source"] != "r/shrinkflation")


def test_history_is_chronological_and_ends_at_current_size(datasets):
    products = {p["product_id"]: p for p in datasets["products.json"]}
    by_product = {}
    for rec in datasets["product_history.json"]:
        by_product.setdefault(rec["product_id"], []).append(rec)
    for pid, recs in by_product.items():
        dates = [r["record_date"] for r in recs]
        assert dates == sorted(dates), pid
        assert recs[-1]["size"] == products[pid]["current_size"]


def test_category_rollups_match_products(datasets):
    for cat in datasets["categories.json"]:
        members = [p for p in datasets["products.json"] if p["category"] == cat["category_name"]]
        affected = [p for p in members if p["shrinkflation_flag"]]
        assert cat["total_products"] == len(members)
        assert cat["affected_products"] == len(affected)


def test_processed_files_are_valid_json():
    for fname in INDEX_FILES.values():
        json.loads((PROCESSED / fname).read_text(encoding="utf-8"))
