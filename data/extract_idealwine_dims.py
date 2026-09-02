#!/usr/bin/env python3
"""Extract the iDealwine reference dimensions (region, appellation,
classification, color, variety) from the normalized JSON files.

Materializes the Google Drive files on first read and writes distinct values to
reference/idealwine_dimensions.csv for later canonical-table construction.
"""
import csv
import glob
import json
import os
import sys
from collections import Counter

BASE = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise/IDealwine_normalized")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                   "reference", "idealwine_dimensions.csv")


def main():
    files = sorted(glob.glob(os.path.join(BASE, "*", "*.json")))
    region = Counter()
    appellation = Counter()
    classification = Counter()
    color = Counter()
    done = 0
    errors = 0
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception as e:  # noqa: BLE001
            errors += 1
            if errors <= 5:
                print(f"ERR {f}: {e}", file=sys.stderr)
            continue
        if d.get("region"):
            region[d["region"]] += 1
        if d.get("appellation"):
            appellation[d["appellation"]] += 1
        if d.get("classification"):
            classification[d["classification"]] += 1
        if d.get("color"):
            color[d["color"]] += 1
        done += 1
        if done % 2000 == 0:
            print(f"  {done}/{len(files)}", flush=True)

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["dimension", "value", "count"])
        for dim, counter in (("region", region), ("appellation", appellation),
                             ("classification", classification),
                             ("color", color)):
            for value, count in sorted(counter.items(),
                                       key=lambda x: (-x[1], x[0])):
                w.writerow([dim, value, count])

    print(f"done={done} errors={errors}")
    print(f"region={len(region)} appellation={len(appellation)} "
          f"classification={len(classification)} color={len(color)}")
    print(f"written: {OUT}")


if __name__ == "__main__":
    main()
