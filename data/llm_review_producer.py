#!/usr/bin/env python3
"""Offline DeepSeek review for producer-in-name extraction.

Reads the ambiguous review CSV, asks DeepSeek to split name+producer per entry,
and writes:

- ``OUT_OVERRIDES``: confident answers as ``MERGE`` override candidates;
- ``OUT_REST``: null/uncertain answers (or unparseable/errored batches) for
  human review.

Batches run in parallel (``--workers``) and the run is resumable: processed
batch indices are recorded in ``OUT_STATE``, so a restart continues where it
left off. This tool is OFFLINE and is never part of the build.
"""
import argparse
import csv
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import requests

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-flash"

IN_CSV = "reference/wine_producer_review.csv"
OUT_OVERRIDES = "reference/wine_llm_overrides.csv"
OUT_REST = "reference/wine_llm_rest.csv"
OUT_STATE = "reference/wine_llm_overrides.csv.state"

SYSTEM = (
    "Du bist ein Wein-Datenbereiniger. Ich gebe dir eine nummerierte Liste von "
    "Wein-Eintraegen; jeder hat \"name\" (voller Text) und optional "
    "\"producer\" (ein bereits bekanntes Produzenten-Feld).\n"
    "Fuer jeden Eintrag liefere:\n"
    "- \"wine\": der Name OHNE den Produzenten (Jahrgang und Flaschenformat "
    "bleiben im Namen).\n"
    "- \"producer\": der Produzent (Weingut). Falls nicht erkennbar: null.\n"
    "Regeln:\n"
    "- Steht der Produzent im Namen (z. B. als Suffix), entferne ihn aus "
    "\"wine\" und nimm ihn in \"producer\" auf.\n"
    "- Der Jahrgang (Jahreszahl) bleibt im \"wine\".\n"
    "- Bei Unsicherheit setze BEIDE Felder auf null.\n"
    "Antworte AUSSCHLIESSLICH als gueltiges JSON-Objekt der Form:\n"
    "{\"results\": [{\"idx\": 0, \"wine\": \"...\", \"producer\": \"...\"}, ...]}"
)

OVERRIDE_FIELDS = ["alias_raw", "producer_raw", "canonical_name", "action",
                   "reason"]
REST_FIELDS = ["canonical_name", "producer", "reason"]


def _load_key():
    if os.environ.get("DEEPSEEK_API_KEY"):
        return os.environ["DEEPSEEK_API_KEY"]
    path = os.path.join(REPO, ".env_local")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line.startswith("DEEPSEEK_API_KEY="):
                    return line.split("=", 1)[1].strip()
    return None


def _load_entries(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return [(r["canonical_name"], r["producer"]) for r in csv.DictReader(fh)]


def _load_state(path):
    if not os.path.exists(path):
        return set()
    with open(path, encoding="utf-8") as fh:
        return {int(line.strip()) for line in fh if line.strip()}


def _ask(session, key, entries):
    user = "\n".join(
        f'{i}: name={json.dumps(name)}, producer={json.dumps(prod or "")}'
        for i, (name, prod) in enumerate(entries))
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user},
        ],
        "response_format": {"type": "json_object"},
        "temperature": 0,
        "thinking": {"type": "disabled"},
    }
    for attempt in range(6):
        resp = session.post(
            BASE_URL,
            headers={"Authorization": f"Bearer {key}"},
            json=payload, timeout=180)
        if resp.status_code == 429:
            wait = max(int(resp.headers.get("Retry-After", "30")), 15)
            time.sleep(wait)
            continue
        try:
            resp.raise_for_status()
            data = resp.json()
            return json.loads(data["choices"][0]["message"]["content"])
        except Exception:  # noqa: BLE001
            if attempt == 5:
                raise
            time.sleep(2 ** attempt)
    return None


def _process_batch(key, batch):
    session = requests.Session()
    try:
        payload = _ask(session, key, batch)
    except Exception as exc:  # noqa: BLE001
        return [], [(name, prod, f"error: {type(exc).__name__}")
                    for name, prod in batch]
    results = {r["idx"]: r for r in payload.get("results", [])}
    overrides = []
    rest = []
    for i, (name, prod) in enumerate(batch):
        r = results.get(i)
        if not r or not r.get("wine") or not r.get("producer"):
            rest.append((name, prod, "null/uncertain"))
        else:
            # The model sometimes strips only the producer token itself,
            # leaving the comma that separated it from the rest of the
            # name (e.g. "ZD Wines, Petit Abacus..." -> ", Petit Abacus...").
            # Confirmed real cases, 6 of 9435 in one run -- small but a
            # real, mechanical leftover, not a guess.
            wine = r["wine"].strip().lstrip(",").strip()
            overrides.append((name, r["producer"], wine))
    return overrides, rest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    key = _load_key()
    if not args.dry_run and not key:
        print("no DEEPSEEK_API_KEY (env or .env_local)", file=sys.stderr)
        return 1

    entries = _load_entries(IN_CSV)
    if args.limit:
        entries = entries[: args.limit]
    batches = [entries[i:i + args.batch]
               for i in range(0, len(entries), args.batch)]

    if args.dry_run:
        print(f"entries: {len(entries)}, batches: {len(batches)}, "
              f"workers: {args.workers}")
        print(json.dumps({
            "model": MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": "\n".join(
                    f'{i}: name={json.dumps(n)}, producer={json.dumps(p or "")}'
                    for i, (n, p) in enumerate(batches[0][:3]))},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }, ensure_ascii=False, indent=2))
        return 0

    done = _load_state(OUT_STATE)
    pending = [(i, b) for i, b in enumerate(batches) if i not in done]
    print(f"total batches: {len(batches)}, already done: {len(done)}, "
          f"pending: {len(pending)}", flush=True)

    n_ov = n_rs = 0
    done_n = len(done)

    def work(item):
        return item[0], _process_batch(key, item[1])

    new_ov = not os.path.exists(OUT_OVERRIDES)
    new_rs = not os.path.exists(OUT_REST)
    with open(OUT_OVERRIDES, "a", newline="", encoding="utf-8") as fh_ov, \
            open(OUT_REST, "a", newline="", encoding="utf-8") as fh_rs:
        w_ov = csv.writer(fh_ov)
        w_rs = csv.writer(fh_rs)
        if new_ov:
            w_ov.writerow(OVERRIDE_FIELDS)
        if new_rs:
            w_rs.writerow(REST_FIELDS)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for b_idx, (ov, rs) in pool.map(work, pending):
                w_ov.writerows(
                    (a, p, c, "MERGE", "llm-review") for a, p, c in ov)
                w_rs.writerows(rs)
                fh_ov.flush()
                fh_rs.flush()
                n_ov += len(ov)
                n_rs += len(rs)
                done.add(b_idx)
                done_n += 1
                with open(OUT_STATE, "a", encoding="utf-8") as fh:
                    fh.write(f"{b_idx}\n")
                if done_n % 50 == 0:
                    print(f"progress {done_n}/{len(batches)} "
                          f"(overrides {n_ov}, rest {n_rs})", flush=True)

    print(f"\noverrides: {n_ov} -> {OUT_OVERRIDES}")
    print(f"rest: {n_rs} -> {OUT_REST}")


if __name__ == "__main__":
    sys.exit(main())
