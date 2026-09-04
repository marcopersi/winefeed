"""Grape-variety matching inside wine names.

Grapes are rarely a standalone field; they are embedded in the wine name
(e.g. "Penfolds Bin 707 Cabernet Sauvignon"). This module detects them by
word-boundary substring matching against the curated varieties.csv.
"""
import csv
import os
import re

from .normalize import normalize


def load_varieties(path):
    """Return a list of (name, color) tuples from the curated varieties CSV."""
    with open(path, encoding="utf-8") as fh:
        return [(r["name"], r["color"]) for r in csv.DictReader(fh)]


def match_varieties(name, variety_keys):
    """Return the set of normalized variety keys present in ``name``."""
    key = normalize(name)
    found = set()
    for v in variety_keys:
        if re.search(rf"\b{re.escape(v)}\b", key):
            found.add(v)
    return found


def default_varieties_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reference", "varieties.csv")
