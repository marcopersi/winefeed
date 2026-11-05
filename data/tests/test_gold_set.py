"""Gold-set regression test for the normalization (§4.0).

Measures vintage + bottle extraction accuracy against hand-labeled lots.
Fails until the gold set has enough labels (entry condition).
"""
import csv
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution.vintage import resolve_vintage  # noqa: E402
from wine_resolution.bottle import parse_bottle_format  # noqa: E402

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "gold_lots.csv")
MIN_LABELED = 50
MIN_ACCURACY = 0.8


def _load():
    with open(FIXTURE, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _eq(actual, expected):
    if expected == "":
        return True
    try:
        return float(actual) == float(expected)
    except (TypeError, ValueError):
        return str(actual) == expected


class TestGoldSet(unittest.TestCase):
    def test_vintage_extraction(self):
        rows = _load()
        labeled = [r for r in rows if r["expected_vintage"].strip()]
        self.assertGreaterEqual(
            len(labeled), MIN_LABELED,
            f"gold set needs >= {MIN_LABELED} labeled vintages "
            f"(got {len(labeled)})")
        correct = 0
        for r in labeled:
            res = resolve_vintage(r["raw_wine"], None, None)
            expected = r["expected_vintage"].strip()
            actual = (str(res["final"])
                      if res["final"] is not None else res["status"])
            if actual == expected:
                correct += 1
        acc = correct / len(labeled)
        self.assertGreaterEqual(
            acc, MIN_ACCURACY,
            f"vintage accuracy {acc:.2%} < {MIN_ACCURACY:.0%} "
            f"({correct}/{len(labeled)})")

    def test_bottle_format(self):
        rows = _load()
        labeled = [r for r in rows if r["expected_qty"].strip()
                   or r["expected_dl"].strip()]
        self.assertGreaterEqual(
            len(labeled), MIN_LABELED,
            f"gold set needs >= {MIN_LABELED} labeled bottles "
            f"(got {len(labeled)})")
        correct = 0
        for r in labeled:
            qty, dl = parse_bottle_format(r["raw_wine"], r["description"])
            ok_qty = _eq(qty, r["expected_qty"].strip())
            ok_dl = _eq(dl, r["expected_dl"].strip())
            if ok_qty and ok_dl:
                correct += 1
        acc = correct / len(labeled)
        self.assertGreaterEqual(
            acc, MIN_ACCURACY,
            f"bottle accuracy {acc:.2%} < {MIN_ACCURACY:.0%} "
            f"({correct}/{len(labeled)})")


if __name__ == "__main__":
    unittest.main()
