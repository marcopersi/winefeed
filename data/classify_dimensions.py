#!/usr/bin/env python3
"""Classify distinct raw region/producer values into canonical dimensions.

First heuristic pass. Counts are real lot counts (for prioritisation). Produces
reference CSVs (region, appellation, classification, variety, producer
remainder) for manual review.
"""
import csv
import os
import re
import sqlite3

from wine_resolution.normalize import normalize

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(SCRIPT_DIR, "wine_auction_prices.sqlite")
REF = os.path.join(SCRIPT_DIR, "reference")


def _load_varieties():
    path = os.path.join(REF, "varieties.csv")
    with open(path, encoding="utf-8") as fh:
        return {normalize(r["name"]) for r in csv.DictReader(fh)}


VARIETIES = _load_varieties()

REGIONS = {
    "bordeaux", "bourgogne", "burgundy", "rhone", "champagne", "alsace",
    "loire", "languedoc", "roussillon", "provence", "jura", "savoie",
    "tuscany", "toscana", "piemonte", "piemont", "veneto", "lombardia",
    "lombardy", "puglia", "sicilia", "sicily", "sardegna", "sardinia",
    "abruzzo", "trentino", "friuli", "alto adige",
    "barossa valley", "barossa", "clare valley", "coonawarra",
    "mclaren vale", "eden valley", "margaret river", "hunter valley",
    "napa valley", "sonoma", "adelaide",
    "rioja", "ribera del duero", "penedes", "priorat", "douro", "mosel",
    "rheingau", "pfalz", "baden", "rheinhessen", "burgenland",
    "marlborough", "central otago", "hawkes bay",
}

APPELLATIONS = {
    "pauillac", "margaux", "saint julien", "saint estephe", "sauternes",
    "pessac leognan", "saint emilion", "pomerol", "medoc", "haut medoc",
    "gevrey chambertin", "chambolle musigny", "vosne romanee", "chablis",
    "meursault", "puligny montrachet", "montrachet", "corton charlemagne",
    "echezeaux", "richebourg", "la tache", "romanee conti",
    "barolo", "barbaresco", "brunello di montalcino", "chianti classico",
    "amarone", "valpolicella", "barbera d asti", "asti", "langhe",
    "chateauneuf du pape", "hermitage", "cote rotie", "gigondas",
    "pouilly fuisse", "sancerre", "vouvray", "muscadet",
}

_CLASSIFICATION_RE = re.compile(
    r"\b(grand cru( classe)?|premier cru|premier grand cru|cru classe|"
    r"cru bourgeois|[1-5]er|2eme|3eme|4eme|5eme|1er grand cru)\b",
    re.IGNORECASE)


def classify(value):
    key = normalize(value)
    if not key:
        return "producer"
    if key in VARIETIES:
        return "variety"
    if key in REGIONS:
        return "region"
    if key in APPELLATIONS:
        return "appellation"
    if _CLASSIFICATION_RE.search(value):
        return "classification"
    return "producer"


def main():
    conn = sqlite3.connect(DB)
    buckets = {"region": {}, "appellation": {}, "classification": {},
               "variety": {}, "producer": {}}

    def add(dim, value, count, source):
        if value not in buckets[dim]:
            buckets[dim][value] = [0, source]
        buckets[dim][value][0] += count

    # producer field, with real counts
    for value, count in conn.execute(
            "SELECT producer, count(*) FROM lots WHERE producer IS NOT NULL"
            " AND producer != '' GROUP BY producer"):
        add(classify(value), value, count, "other")
    # region field, with real counts
    for value, count in conn.execute(
            "SELECT region, count(*) FROM lots WHERE region IS NOT NULL"
            " AND region != '' GROUP BY region"):
        dim = classify(value)
        if dim == "producer":
            dim = "region"
        add(dim, value, count, "other")
    # idealwine classification (already canonical)
    for value, count in conn.execute(
            "SELECT classification, count(*) FROM lots WHERE classification"
            " IS NOT NULL AND classification != '' GROUP BY classification"):
        add("classification", value, count, "idealwine")
    # idealwine region (canonical base)
    for value, count in conn.execute("""
            SELECT l.region, count(*) FROM lots l
            JOIN auctions a ON l.auction_id=a.id
            JOIN providers p ON a.provider_id=p.id
            WHERE p.name='idealwine' AND l.region IS NOT NULL
            GROUP BY l.region"""):
        add("region", value, count, "idealwine")

    for dim in ("region", "appellation", "classification", "variety",
                "producer"):
        path = os.path.join(REF, f"dim_{dim}.csv")
        with open(path, "w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow(["value", "lots", "source", "keep"])
            for value, (count, source) in sorted(
                    buckets[dim].items(), key=lambda x: (-x[1][0], x[0])):
                w.writerow([value, count, source, ""])
        print(f"{dim:14} {len(buckets[dim]):6}  -> reference/dim_{dim}.csv")


if __name__ == "__main__":
    main()
