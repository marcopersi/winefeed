"""Spirits detection for filtering non-wine lots.

A curated list of spirit categories and brand names. Lots whose name contains
one of these terms are not wine and should be excluded from wine analysis.
"""
import csv
import os
import re

from .normalize import normalize


def _default_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "reference", "spirits_terms.csv")


def load_terms(path=None):
    path = path or _default_path()
    with open(path, encoding="utf-8") as fh:
        return [normalize(r["term"]) for r in csv.DictReader(fh)]


def is_spirit(name, terms):
    """True if ``name`` contains any of the normalized spirit terms."""
    key = normalize(name)
    if not key:
        return False
    return any(re.search(rf"\b{re.escape(t)}\b", key) for t in terms)
