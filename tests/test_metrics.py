"""Unit tests for the shrinkflation math used by the pipeline."""

import pytest
from data_pipeline import (
    effective_price_increase_pct,
    make_upc,
    price_per_unit,
    severity,
    shrinkage_pct,
    year_after,
    year_before,
)


def test_shrinkage_pct_doritos():
    # 9.75 oz -> 9.25 oz is a 5.1% smaller bag
    assert shrinkage_pct(9.75, 9.25) == 5.1


@pytest.mark.parametrize("old,new", [(10.0, 10.0), (10.0, 12.0)])
def test_shrinkage_pct_is_zero_when_not_shrunk(old, new):
    assert shrinkage_pct(old, new) == 0.0


def test_price_per_unit_rounds_to_four_places():
    assert price_per_unit(4.99, 9.25) == 0.5395


def test_effective_increase_same_price_smaller_pack():
    # Same $4.99 sticker price, less product: per-ounce price rises 5.4%
    assert effective_price_increase_pct(4.99, 9.75, 4.99, 9.25) == 5.4


def test_effective_increase_combines_price_and_size_change():
    # Tostitos: 10 oz @ $4.79 -> 9.25 oz @ $4.99
    assert effective_price_increase_pct(4.79, 10.0, 4.99, 9.25) == 12.6


def test_effective_increase_exceeds_shrinkage():
    # Losing x% of the product at the same price costs more than x% per unit.
    assert effective_price_increase_pct(5.0, 20.0, 5.0, 15.0) > shrinkage_pct(20.0, 15.0)


@pytest.mark.parametrize(
    "pct,expected",
    [(0.0, "low"), (6.9, "low"), (7.0, "medium"), (14.9, "medium"), (15.0, "high"), (40.0, "high")],
)
def test_severity_thresholds(pct, expected):
    assert severity(pct) == expected


def test_make_upc_is_stable_and_well_formed():
    upc = make_upc("doritos-nacho-001")
    assert upc == make_upc("doritos-nacho-001")
    assert len(upc) == 12 and upc.isdigit() and upc.startswith("0")
    assert upc != make_upc("lays-classic-001")


def test_year_shift_helpers():
    assert year_before("2022-03-15", 2) == "2020-03-15"
    assert year_after("2022-03-15") == "2023-03-15"
