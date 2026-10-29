#!/usr/bin/env python3
"""Build wine_auction_prices.sqlite from scratch (repeatable, deterministic).

Reads all structured auction data (14 JSON houses in the Google Drive archive
plus the Wermuth and Steinfels Excel/CSV in the winefeed repo) and writes a
single normalized SQLite database.

Every run drops and recreates the schema, so the result is fully reproducible:
    python3 build_db.py            # full build
    python3 build_db.py --limit 20 # dry run on a few files per house
    python3 build_db.py --dry-run  # no write
"""
import argparse
import csv
import datetime
import glob
import json
import os
import re
import sqlite3
import sys

import openpyxl

# Source of raw auction data. Override via env vars:
#   ARCHIVE_PATH=/path/to/archive DB_PATH=/path/to/output.sqlite python3 build_db.py
ARCHIVE = os.environ.get("ARCHIVE_PATH", os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/"
    "Meine Ablage/Wein/WeinAuktionspreise"))

# Repo root (contains the Wermuth/Steinfels Excel files). The SQLite output goes
# to the Samsung disk by default (it is the master copy and is not committed).
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(SCRIPT_DIR)
DB_PATH = os.environ.get(
    "DB_PATH", "/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite")

# --------------------------------------------------------------------------- #
# Schema
# --------------------------------------------------------------------------- #

SCHEMA = """
DROP TABLE IF EXISTS wine_varieties;
DROP TABLE IF EXISTS wine_origin_mappings;
DROP TABLE IF EXISTS wine_alias_resolutions;
DROP TABLE IF EXISTS wine_alias_observations;
DROP TABLE IF EXISTS build_metrics;
DROP TABLE IF EXISTS build_inputs;
DROP TABLE IF EXISTS builds;
DROP TABLE IF EXISTS lots;
DROP TABLE IF EXISTS wine_origins;
DROP TABLE IF EXISTS wines;
DROP TABLE IF EXISTS auctions;
DROP TABLE IF EXISTS providers;

CREATE TABLE providers (
  id   INTEGER PRIMARY KEY,
  name TEXT NOT NULL UNIQUE
);

CREATE TABLE auctions (
  id          INTEGER PRIMARY KEY,
  provider_id INTEGER NOT NULL REFERENCES providers(id),
  auction_id  TEXT,
  title       TEXT,
  auction_date TEXT,
  location    TEXT,
  currency    TEXT,
  price_basis TEXT,
  source_url  TEXT,
  scraped_at  TEXT,
  UNIQUE(provider_id, auction_id)
);

CREATE TABLE wines (
  id               INTEGER PRIMARY KEY,
  stable_key       TEXT NOT NULL UNIQUE,
  canonical_name   TEXT NOT NULL,
  canonical_key    TEXT NOT NULL,
  producer         TEXT,
  producer_key     TEXT,
  region           TEXT,
  appellation      TEXT,
  classification   TEXT,
  canonical_source TEXT NOT NULL,
  resolver_version TEXT NOT NULL,
  review_status    TEXT NOT NULL,
  CHECK (trim(canonical_name) <> ''),
  CHECK (review_status IN (
    'AUTO_RESOLVED', 'CURATED', 'AMBIGUOUS', 'REVIEW_REQUIRED'
  ))
);

CREATE TABLE wine_origins (
  origin_id              TEXT PRIMARY KEY,
  country_code           TEXT,
  country_de             TEXT,
  country_fr             TEXT,
  country_en             TEXT,
  region_canonical       TEXT,
  region_de              TEXT,
  region_fr              TEXT,
  region_en              TEXT,
  appellation_canonical  TEXT,
  record_level           TEXT,
  appellation_type       TEXT,
  legal_scheme           TEXT,
  legal_status           TEXT,
  source_authority       TEXT,
  source_url             TEXT,
  legal_basis_url        TEXT,
  validated_on           TEXT,
  auction_lots_observed  INTEGER,
  notes_de               TEXT,
  notes_fr               TEXT,
  notes_en               TEXT
);

CREATE TABLE wine_origin_mappings (
  id                  INTEGER PRIMARY KEY,
  source_file         TEXT,
  raw_value           TEXT,
  raw_lots            INTEGER,
  raw_source          TEXT,
  raw_country_code    TEXT,
  normalized_value    TEXT,
  match_status        TEXT,
  match_confidence    REAL,
  target_origin_id    TEXT REFERENCES wine_origins(origin_id),
  target_record_level TEXT,
  match_reason        TEXT
);

CREATE TABLE lots (
  id                  INTEGER PRIMARY KEY,
  auction_id          INTEGER NOT NULL REFERENCES auctions(id),
  lot_no              TEXT,
  lot_date            TEXT,
  source_file         TEXT,
  source_file_sha256  TEXT,
  source_record_locator TEXT,
  source_record_hash  TEXT,
  raw_wine            TEXT,
  raw_producer        TEXT,
  raw_vintage         TEXT,
  source_lot_key      TEXT,
  wine                TEXT,
  wine_ref_id         INTEGER REFERENCES wines(id),
  producer            TEXT,
  vintage             INTEGER,
  region              TEXT,
  appellation         TEXT,
  origin_id           TEXT REFERENCES wine_origins(origin_id),
  origin_status       TEXT,
  classification      TEXT,
  color               TEXT,
  vintage_raw         TEXT,
  vintage_extracted   INTEGER,
  vintage_final       INTEGER,
  vintage_status      TEXT,
  vintage_rule_id     TEXT,
  vintage_evidence_text TEXT,
  lot_kind            TEXT,
  mixed_reason        TEXT,
  mixed_rule_id       TEXT,
  mixed_lot           INTEGER,
  quantity            INTEGER,
  bottle_size_dl      REAL,
  estimate_low        REAL,
  estimate_high       REAL,
  hammer_price        REAL,
  buyer_premium       REAL,
  realised_price      REAL,
  fees                REAL,
  tax_amount          REAL,
  total_price         REAL,
  price_source        TEXT,
  price_basis         TEXT,
  currency            TEXT,
  fx_rate             REAL,
  fx_target_currency  TEXT,
  sold                INTEGER,
  condition_text      TEXT,
  description         TEXT,
  source_url          TEXT,
  scraped_at          TEXT,
  is_ohk              INTEGER,
  note                TEXT,
  price_per_bottle    REAL,
  CHECK (vintage_final IS NULL OR vintage_final BETWEEN 1700 AND 2100),
  CHECK (lot_kind IS NULL OR lot_kind IN ('SINGLE', 'MIXED', 'UNKNOWN')),
  CHECK (lot_kind <> 'MIXED' OR wine_ref_id IS NULL),
  CHECK (vintage_status IS NULL OR vintage_status IN (
    'STRUCTURED', 'EXTRACTED', 'NV', 'MV', 'MISSING',
    'AMBIGUOUS', 'CONFLICT', 'INVALID'
  ))
);

CREATE TABLE wine_alias_observations (
  id                 INTEGER PRIMARY KEY,
  provider_id        INTEGER NOT NULL REFERENCES providers(id),
  alias_raw          TEXT NOT NULL,
  alias_key          TEXT NOT NULL,
  producer_raw       TEXT,
  producer_key       TEXT,
  region_raw         TEXT,
  region_key         TEXT,
  source_lot_id      INTEGER REFERENCES lots(id),
  evidence_count     INTEGER NOT NULL,
  normalizer_version TEXT NOT NULL
);

CREATE TABLE wine_alias_resolutions (
  id                INTEGER PRIMARY KEY,
  scope_key         TEXT NOT NULL,
  alias_key         TEXT NOT NULL,
  discriminator_key TEXT NOT NULL,
  wine_id           INTEGER REFERENCES wines(id),
  resolution_status TEXT NOT NULL,
  resolution_method TEXT NOT NULL,
  confidence        REAL,
  rule_version      TEXT NOT NULL,
  reason            TEXT,
  UNIQUE(scope_key, alias_key, discriminator_key),
  CHECK (resolution_status IN (
    'RESOLVED', 'AMBIGUOUS', 'UNRESOLVED', 'IGNORED'
  ))
);

CREATE TABLE wine_varieties (
  id           INTEGER PRIMARY KEY,
  wine_id      INTEGER NOT NULL REFERENCES wines(id),
  variety_name TEXT NOT NULL,
  color        TEXT,
  UNIQUE(wine_id, variety_name)
);

CREATE TABLE builds (
  id                    TEXT PRIMARY KEY,
  started_at            TEXT NOT NULL,
  completed_at          TEXT,
  input_manifest_sha256 TEXT NOT NULL,
  loader_version        TEXT NOT NULL,
  normalizer_version    TEXT NOT NULL,
  resolver_version      TEXT NOT NULL,
  python_version        TEXT NOT NULL,
  sqlite_version        TEXT NOT NULL,
  status                TEXT NOT NULL
);

CREATE TABLE build_inputs (
  build_id         TEXT NOT NULL REFERENCES builds(id),
  source_file      TEXT NOT NULL,
  source_file_sha256 TEXT NOT NULL,
  file_size        INTEGER NOT NULL,
  PRIMARY KEY (build_id, source_file)
);

CREATE TABLE build_metrics (
  build_id TEXT NOT NULL REFERENCES builds(id),
  provider TEXT NOT NULL,
  metric   TEXT NOT NULL,
  value    INTEGER NOT NULL,
  PRIMARY KEY (build_id, provider, metric)
);

CREATE INDEX idx_lots_auction ON lots(auction_id);
CREATE INDEX idx_lots_wine ON lots(wine);
CREATE INDEX idx_lots_hammer ON lots(hammer_price);
CREATE INDEX idx_lots_wine_ref ON lots(wine_ref_id);
CREATE INDEX idx_lots_lot_kind ON lots(lot_kind);
CREATE INDEX idx_lots_source_lot_key ON lots(source_lot_key);

CREATE VIEW single_wine_prices AS
SELECT *
FROM lots
WHERE lot_kind = 'SINGLE'
  AND wine_ref_id IS NOT NULL
  AND vintage_status IN ('STRUCTURED', 'EXTRACTED');
"""

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

MONTHS = {m: i + 1 for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun",
     "jul", "aug", "sep", "oct", "nov", "dec"])}


def load_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def to_float(v):
    """Best-effort numeric conversion (US/UK thousands separator)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        return None
    s = str(v).strip()
    s = s.replace("$", "").replace("€", "").replace("£", "")
    s = s.replace("HK$", "").replace("CHF", "").replace("\u00a0", "")
    s = s.replace(" ", "")
    if s in ("", "-", "null", "None", "—"):
        return None
    if "," in s and "." in s:
        s = s.replace(",", "")
    elif "," in s:
        # "1,434" -> thousands ; "1,5" -> decimal
        if re.fullmatch(r"\d{1,3},\d{3}(,\d{3})*", s):
            s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def euro_int(v):
    """European thousands format: '8.060' -> 8060, '10.000' -> 10000."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, dict):
        return to_float(v.get("value"))
    s = str(v).strip().replace("€", "").replace(" ", "").replace("\u00a0", "")
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def to_int(v):
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return int(v)
    if isinstance(v, bool):
        return None
    s = str(v).strip()
    if s in ("", "null", "None"):
        return None
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group()) if m else None


def parse_date(v):
    if not v:
        return None
    if isinstance(v, dict):
        for k in ("closed", "acceptsBids", "startsToClose", "published"):
            if v.get(k):
                v = v[k]
                break
        else:
            return None
    s = str(v).strip()
    if s.startswith("20") and len(s) >= 10 and s[4] == "-":
        return s[:10]
    m = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", s)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"
    m = re.search(r"(\d{1,2})\s+(\w{3,9})\.?\s+(\d{4})", s)
    if m:
        mon = MONTHS.get(m.group(2).lower()[:3])
        if mon:
            return f"{m.group(3)}-{mon:02d}-{int(m.group(1)):02d}"
    return None


def ym_date(year, month):
    """Year+month -> ISO-ish date (first of month)."""
    if year is None:
        return None
    if month is None:
        return f"{int(year)}-01-01"
    return f"{int(year)}-{int(month):02d}-01"


def parse_dl(v):
    """Bottle size hints -> deciliters (7.5 = 750 ml)."""
    if v is None or v == "":
        return None
    s = str(v).lower()
    m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|l)", s)
    if m:
        n = float(m.group(1))
        return n / 100 if m.group(2) == "ml" else n * 10
    if "magnum" in s or "1.5" in s or "1500" in s:
        return 15.0
    if "jeroboam" in s or "3l" in s or "3000ml" in s:
        return 30.0
    if "half" in s or "375" in s or "3.75" in s:
        return 3.75
    f = to_float(v)
    if f is not None and 1 <= f <= 60:
        return f
    return None


def parse_qty_text(v):
    """'2 Bottles 750ml' -> 2."""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    m = re.search(r"(\d+)", str(v))
    return int(m.group(1)) if m else None


# Fixed auction location for houses bound to one physical saleroom. Houses with
# per-auction locations (sothebys, christies) pass ``location`` explicitly.
PROVIDER_LOCATIONS = {
    "weinboerse": "Zürich",
    "steinfels": "Zürich",
    "baghera": "Genf",
    "dobiaschofsky": "Bern",
    "wermuth-sa": "Zürich",
    "koppe": "Deutschland",
    "weinauktionator": "Deutschland",
    "finarte": "Italien",
    "pandolfini": "Italien",
    "besch-cannes": "Cannes",
    "dorotheum": "Wien",
    "hdh": "Chicago",
    "langtons": "Sydney",
    "idealwine": "Paris",
    "munich-wine-company": "München",
    "winebarrel": "Zürich",
    "winefields": "Amsterdam",
    "zacky": "New York",
}


# --------------------------------------------------------------------------- #
# Insert helpers
# --------------------------------------------------------------------------- #

class Builder:
    def __init__(self, conn):
        self.conn = conn
        self.provider_ids = {}
        self.source_file = None
        self.source_idx = 0

    def provider(self, name):
        if name not in self.provider_ids:
            cur = self.conn.execute(
                "INSERT OR IGNORE INTO providers(name) VALUES (?)", (name,))
            if cur.rowcount == 1:
                self.provider_ids[name] = cur.lastrowid
            else:
                row = self.conn.execute(
                    "SELECT id FROM providers WHERE name = ?",
                    (name,)).fetchone()
                self.provider_ids[name] = row[0]
        return self.provider_ids[name]

    def set_source(self, source_file):
        """Set provenance context for the following add_lot calls."""
        self.source_file = os.path.relpath(source_file, ARCHIVE)
        self.source_idx = 0

    def add_auction(self, provider, auction_id, title=None, date=None,
                    currency=None, price_basis=None, source_url=None,
                    scraped_at=None, location=None):
        pid = self.provider(provider)
        location = location or PROVIDER_LOCATIONS.get(provider)
        cur = self.conn.execute(
            "INSERT OR IGNORE INTO auctions(provider_id, auction_id, title,"
            " auction_date, location, currency, price_basis, source_url,"
            " scraped_at)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            (pid, auction_id, title, date, location, currency, price_basis,
             source_url, scraped_at))
        if cur.rowcount == 1:
            return cur.lastrowid
        row = self.conn.execute(
            "SELECT id FROM auctions WHERE provider_id=? AND auction_id=?",
            (pid, auction_id)).fetchone()
        return row[0]

    def add_lot(self, auction_id, row):
        wine = row.get("wine")
        producer = row.get("producer")
        vintage = row.get("vintage")
        raw_wine = row.get("raw_wine") if "raw_wine" in row else wine
        raw_producer = row.get("raw_producer") if "raw_producer" in row else producer
        raw_vintage = row.get("raw_vintage")
        if raw_vintage is None and vintage is not None:
            raw_vintage = str(vintage)
        source_file = row.get("source_file", self.source_file)
        source_record_locator = row.get("source_record_locator")
        if source_record_locator is None:
            source_record_locator = f"lots[{self.source_idx}]"
            self.source_idx += 1
        cur = self.conn.execute(
            "INSERT INTO lots(auction_id, lot_no, lot_date, source_file,"
            " source_record_locator, raw_wine, raw_producer, raw_vintage,"
            " source_lot_key, wine, wine_ref_id, producer, vintage, region,"
            " appellation, classification, color, quantity, bottle_size_dl,"
            " estimate_low, estimate_high, hammer_price, buyer_premium,"
            " realised_price, fees, tax_amount, total_price, price_source,"
            " price_basis, currency, fx_rate, fx_target_currency,"
            " sold, mixed_lot,"
            " condition_text, description, source_url, scraped_at,"
            " is_ohk, note, price_per_bottle)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            "?,?)",
            (auction_id, row.get("lot_no"), row.get("lot_date"),
             source_file, source_record_locator,
             raw_wine, raw_producer, raw_vintage,
             row.get("source_lot_key"), wine, row.get("wine_ref_id"),
             producer, vintage, row.get("region"),
             row.get("appellation"), row.get("classification"),
             row.get("color"), row.get("quantity"),
             row.get("bottle_size_dl"), row.get("estimate_low"),
             row.get("estimate_high"), row.get("hammer_price"),
             row.get("buyer_premium"), row.get("realised_price"),
             row.get("fees"), row.get("tax_amount"),
             row.get("total_price"), row.get("price_source"),
             row.get("price_basis"), row.get("currency"),
             row.get("fx_rate"), row.get("fx_target_currency"),
             row.get("sold"),
             row.get("mixed_lot"), row.get("condition_text"),
             row.get("description"), row.get("source_url"),
             row.get("scraped_at"), row.get("is_ohk"), row.get("note"),
             row.get("price_per_bottle")))
        return cur.lastrowid


# --------------------------------------------------------------------------- #
# Per-house loaders
# --------------------------------------------------------------------------- #

def _json_files(house, pattern=None):
    base = os.path.join(ARCHIVE, house)
    pat = pattern or "**/*.json"
    files = sorted(glob.glob(os.path.join(base, pat), recursive=True))
    return [f for f in files if not f.endswith("auctions_directory.json")
            and not f.endswith("wines_directory.json")]


def load_baghera(b, limit):
    n = 0
    for f in _json_files("Baghera", "**/auction-*.json"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        cur = a.get("currency") or "CHF"
        a_id = b.add_auction(
            "baghera", aid, a.get("title"), ym_date(a.get("year"), a.get("month")),
            cur, "HAMMER", a.get("results_pdf"))
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": None, "description": lot.get("description"),
                "hammer_price": to_float(lot.get("hammer")),
                "realised_price": to_float(lot.get("total_price")),
                "buyer_premium": to_float(lot.get("buyer_premium")),
                "price_basis": "HAMMER", "currency": lot.get("currency") or cur,
            })
        n += 1
        if limit and n >= limit:
            break


def load_hdh(b, limit):
    n = 0
    for f in _json_files("HDH"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("sale_number"))
        a_id = b.add_auction(
            "hdh", aid, a.get("name"), ym_date(a.get("year"), a.get("month")),
            "USD", "HAMMER")
        for lot in d.get("lots", []):
            hammer = to_float(lot.get("hammer"))
            aggregate = to_float(lot.get("aggregate"))
            if hammer is not None:
                basis = "HAMMER"
            elif aggregate is not None:
                basis = "HAMMER_PLUS_BUYERS_PREMIUM"
            else:
                basis = "UNKNOWN"
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("wine"), "producer": lot.get("grower"),
                "vintage": to_int(lot.get("vintage")),
                "quantity": to_int(lot.get("qty")),
                "bottle_size_dl": parse_dl(lot.get("size")),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                "hammer_price": hammer,
                "realised_price": aggregate,
                "price_basis": basis, "currency": "USD",
                "mixed_lot": 1 if lot.get("mixed_lot") else None,
                "condition_text": lot.get("condition"),
                "description": lot.get("description"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_weinauktionator(b, limit):
    n = 0
    for f in _json_files("weinauktionator"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        m = re.search(r"results_(\d+)", os.path.basename(f))
        aid = m.group(1) if m else (a.get("id") or a.get("date") or "")
        a_id = b.add_auction(
            "weinauktionator", aid, a.get("name"),
            parse_date(a.get("date")), "EUR", "HAMMER")
        for lot in d.get("lots", []):
            qty, size = _winauktionator_qty_size(lot.get("format"))
            hammer = to_float(lot.get("hammer_price"))
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("wine"),
                "region": lot.get("region"),
                "quantity": qty,
                "bottle_size_dl": size,
                "hammer_price": hammer,
                "price_basis": "HAMMER" if hammer is not None else "UNKNOWN",
                "currency": "EUR",
                "sold": 1 if hammer is not None else 0,
                "description": lot.get("format"),
            })
        n += 1
        if limit and n >= limit:
            break


def _winauktionator_qty_size(fmt):
    """'3 x 0.750 ...' -> (3, 7.5)."""
    m = re.match(r"(\d+)\s*x\s*(\d+(?:\.\d+)?)", fmt or "")
    if m:
        return int(m.group(1)), round(float(m.group(2)) * 10, 2)
    return None, None


def load_winefields(b, limit):
    n = 0
    for f in _json_files("Winefields"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("auction_id"))
        a_id = b.add_auction(
            "winefields", aid, a.get("title"),
            parse_date(a.get("time_start")), None, "HAMMER")
        for lot in d.get("lots", []):
            cur = lot.get("currency")
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("title"),
                "quantity": to_int(lot.get("quantity")),
                "bottle_size_dl": parse_dl(lot.get("size")),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                "hammer_price": to_float(lot.get("hammer")),
                "price_basis": "HAMMER", "currency": cur,
                "sold": 1 if lot.get("status") == "sold" else 0,
                "mixed_lot": 1 if lot.get("is_mixed_lot") else 0,
                "condition_text": lot.get("condition"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_beschcannes(b, limit):
    n = 0
    for f in _json_files("BeschCannes", "**/auction-*.json"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        cur = a.get("currency") or "EUR"
        a_id = b.add_auction(
            "besch-cannes", aid, a.get("slug"), parse_date(a.get("date")),
            cur, a.get("price_basis") or "HAMMER")
        for lot in d.get("lots", []):
            sold = 1 if lot.get("adjuge") not in (None, "") else 0
            est = lot.get("estimate")
            est_low = est[0] if isinstance(est, list) and len(est) > 0 else None
            est_high = est[1] if isinstance(est, list) and len(est) > 1 else None
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("appellation"),
                "vintage": to_int(lot.get("vintage")),
                "estimate_low": to_float(est_low),
                "estimate_high": to_float(est_high),
                "hammer_price": to_float(lot.get("hammer") or lot.get("adjuge")),
                "price_basis": "HAMMER", "currency": cur, "sold": sold,
                "description": lot.get("description"),
                "condition_text": lot.get("remarks"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_langtons(b, limit):
    n = 0
    for f in _json_files("Langtons"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        a_id = b.add_auction(
            "langtons", aid, a.get("name"), parse_date(a.get("date")),
            "AUD", "HAMMER")
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot")),
                "wine": lot.get("wine"), "region": lot.get("region"),
                "classification": lot.get("classification") or None,
                "vintage": to_int(lot.get("vintage")),
                "quantity": to_int(lot.get("quantity")),
                "hammer_price": to_float(lot.get("winning_bid")),
                "price_basis": "HAMMER",
                "currency": lot.get("currency") or "AUD",
                "condition_text": lot.get("notes"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_sothebys(b, limit):
    n = 0
    for f in _json_files("Sothebys"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("auction_id"))
        cur = a.get("currency")
        a_id = b.add_auction(
            "sothebys", aid, a.get("title"), parse_date(a.get("dates")),
            cur, "HAMMER", location=a.get("location"))
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_number")),
                "wine": lot.get("title"),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                "hammer_price": to_float(lot.get("hammer_price")),
                "realised_price": to_float(lot.get("final_price")),
                "price_basis": "HAMMER",
                "currency": lot.get("currency") or cur,
                "sold": 1 if lot.get("sold") else 0,
            })
        n += 1
        if limit and n >= limit:
            break


def load_christies(b, limit):
    n = 0
    for f in _json_files("Christies"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("event_id") or a.get("sale_id"))
        a_id = b.add_auction(
            "christies", aid, a.get("title"),
            ym_date(a.get("year"), a.get("month")), None, "HAMMER",
            a.get("landing_url"), location=a.get("location"))
        for lot in d.get("lots", []):
            sold = 1 if (lot.get("price_realised") and
                         not lot.get("lot_withdrawn")) else 0
            price = to_float(lot.get("price_realised"))
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_number")),
                "wine": lot.get("title"),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                # Christie's "price realised" is gross (incl. 25% wine buyer's
                # premium); back out the net hammer and keep the gross as
                # realised_price. Historic NLG lots used 20.825% — approximated
                # with 25% here.
                "hammer_price": round(price / 1.25, 2)
                if price is not None else None,
                "realised_price": price,
                "price_basis": "HAMMER",
                "currency": lot.get("currency"),
                "sold": sold,
                "description": lot.get("description"),
                "source_url": lot.get("url"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_zacky(b, limit):
    n = 0
    for f in _json_files("Zacky", "**/auction-*.json"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        cur = a.get("currency")
        a_id = b.add_auction(
            "zacky", aid, a.get("name"), ym_date(a.get("year"), a.get("month")),
            cur, "HAMMER_PLUS_BUYERS_PREMIUM",
            a.get("snapshot_url"), a.get("snapshot_timestamp"))
        for lot in d.get("lots", []):
            fp = lot.get("final_price")
            sold = 1 if (fp and fp > 0) else 0
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("name"),
                "quantity": parse_qty_text(lot.get("quantity")),
                "bottle_size_dl": parse_dl(lot.get("quantity")),
                "realised_price": to_float(fp) if fp else None,
                "price_basis": "HAMMER_PLUS_BUYERS_PREMIUM",
                "currency": cur, "sold": sold,
                "description": lot.get("description"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_finarte(b, limit):
    n = 0
    for f in _json_files("Finarte"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("slug"))
        a_id = b.add_auction(
            "finarte", aid, a.get("name"), parse_date(a.get("date")),
            "EUR", "HAMMER")
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_nr")),
                "wine": lot.get("name"), "region": lot.get("region"),
                "vintage": to_int(lot.get("vintage")),
                "estimate_low": to_float(lot.get("estimate_min")),
                "estimate_high": to_float(lot.get("estimate_max")),
                "hammer_price": to_float(lot.get("hammer_price")),
                "price_basis": "HAMMER",
                "currency": lot.get("currency") or "EUR",
                "sold": 1 if lot.get("sold") else 0,
                "condition_text": lot.get("vat_regime"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_dorotheum(b, limit):
    n = 0
    for f in _json_files("Dorotheum"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        a_id = b.add_auction(
            "dorotheum", aid, a.get("name"), parse_date(a.get("date")),
            "EUR", "HAMMER")
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_nr")),
                "wine": lot.get("name"),
                "estimate_low": to_float(lot.get("estimate")),
                "estimate_high": to_float(lot.get("estimate")),
                "hammer_price": to_float(lot.get("realized_price")),
                "price_basis": "HAMMER",
                "currency": lot.get("currency") or "EUR",
                "sold": 1 if lot.get("sold") else 0,
                "description": lot.get("description"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_pandolfini(b, limit):
    n = 0
    for f in _json_files("Pandolfini"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        a_id = b.add_auction(
            "pandolfini", aid, a.get("name"), parse_date(a.get("date")),
            "EUR", "HAMMER_PLUS_BUYERS_PREMIUM")
        for lot in d.get("lots", []):
            sp = lot.get("sold_price") or {}
            sold = 1 if sp.get("class") == "venduto" else 0
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_nr")),
                "wine": lot.get("name"),
                "estimate_low": euro_int(lot.get("estimate_low")),
                "estimate_high": euro_int(lot.get("estimate_high")),
                "realised_price": euro_int(sp.get("value")) if sp else None,
                "price_basis": "HAMMER_PLUS_BUYERS_PREMIUM",
                "currency": "EUR", "sold": sold,
                "description": lot.get("description"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_koppe(b, limit):
    n = 0
    for f in _json_files("Koppe"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        a_id = b.add_auction("koppe", aid, a.get("name"),
                             parse_date(a.get("date")), "EUR", "HAMMER")
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("name"),
                "region": lot.get("region"),
                "vintage": to_int(lot.get("vintage")),
                "color": lot.get("color") or None,
                "bottle_size_dl": parse_dl(
                    (lot.get("bottle_size") or "").replace(",", ".") or None),
                "hammer_price": to_float(lot.get("hammer_price")),
                "price_basis": "HAMMER", "currency": "EUR",
                "description": ", ".join(lot.get("format") or []) or None,
            })
        n += 1
        if limit and n >= limit:
            break


def _load_weinauktion_json(b, provider, limit):
    """Load the weinauktion-platform API JSON (steinfels / weinboerse)."""
    n = 0
    for f in _json_files(provider):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        a_id = b.add_auction(provider, aid, a.get("name"),
                             parse_date(a.get("date")),
                             a.get("currency") or "CHF", "HAMMER")
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("wine"),
                "vintage": to_int(lot.get("vintage")),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                "hammer_price": to_float(lot.get("hammer_price")),
                "price_basis": "HAMMER",
                "currency": lot.get("currency") or "CHF",
                "sold": 1 if lot.get("sold") else 0,
            })
        n += 1
        if limit and n >= limit:
            break
    return n


def load_weinboerse(b, limit):
    _load_weinauktion_json(b, "weinboerse", limit)


def load_dobiaschofsky(b, limit):
    n = 0
    for f in _json_files("Dobiaschofsky", "**/auktion-*.json"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        a_id = b.add_auction(
            "dobiaschofsky", aid, a.get("name"), parse_date(a.get("date")),
            "CHF", "HAMMER")
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_nr")),
                "wine": lot.get("name"),
                "vintage": to_int(lot.get("vintage")),
                "estimate_low": to_float(lot.get("estimate_chf")),
                "estimate_high": to_float(lot.get("estimate_chf")),
                "hammer_price": to_float(lot.get("hammer_chf")),
                "price_basis": "HAMMER", "currency": "CHF",
                "description": lot.get("description"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_munich_wine_company(b, limit):
    n = 0
    for f in _json_files("MunichWineCompany"):
        d = load_json(f)
        b.set_source(f)
        a = d.get("auction", {})
        aid = str(a.get("id"))
        cur = a.get("currency") or "EUR"
        a_id = b.add_auction(
            "munich-wine-company", aid, a.get("title"),
            parse_date(a.get("date")), cur, "HAMMER",
            None, a.get("snapshot_timestamp"))
        for lot in d.get("lots", []):
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("name"), "producer": lot.get("brand") or None,
                "quantity": parse_qty_text(lot.get("count_fill")),
                "hammer_price": to_float(lot.get("hammer_price")),
                "price_basis": "HAMMER",
                "currency": lot.get("currency") or cur,
                "description": lot.get("description"),
                "condition_text": lot.get("count_fill"),
            })
        n += 1
        if limit and n >= limit:
            break


def load_winebarrel(b, limit):
    f = os.path.join(ARCHIVE, "winebarrel", "winebarrel_lots.json")
    if not os.path.exists(f):
        return
    d = load_json(f)
    b.set_source(f)
    # one virtual auction holding everything
    a_id = b.add_auction("winebarrel", "all", "winebarrel", None, None, "HAMMER")
    for i, lot in enumerate(d):
        if limit and i >= limit:
            break
        b.add_lot(a_id, {
            "lot_no": str(lot.get("auction_id")),
            "lot_date": parse_date(lot.get("auction_end")),
            "wine": lot.get("name"), "producer": lot.get("winery"),
            "vintage": to_int(lot.get("vintage")),
            "quantity": to_int(lot.get("bottles")),
            "region": lot.get("region"),
            "hammer_price": to_float(lot.get("hammer_price")),
            "price_basis": "HAMMER",
        })


def load_idealwine(b, limit):
    n = 0
    for f in _json_files("IDealwine_normalized"):
        d = load_json(f)
        b.set_source(f)
        aid = "cote"
        a_id = b.add_auction(
            "idealwine", aid, f"iDealwine Cote {d.get('region')}",
            None, "EUR", None)
        for a in d.get("adjudications", []):
            basis = a.get("price_basis")
            b.add_lot(a_id, {
                "lot_no": a.get("code"),
                "lot_date": parse_date(a.get("sold_at")),
                "wine": d.get("wine"), "producer": d.get("estate"),
                "vintage": to_int(d.get("vintage")),
                "region": d.get("region"),
                "appellation": d.get("appellation") or None,
                "classification": d.get("classification") or None,
                "color": d.get("color") or None,
                "quantity": to_int(a.get("number_of_bottles")),
                "bottle_size_dl": parse_dl(a.get("format")),
                "hammer_price": a.get("hammer_per_bottle_eur")
                or a.get("hammer_per_bottle_eur_derived"),
                "realised_price": a.get("total_per_bottle_eur"),
                "price_basis": basis, "currency": "EUR",
            })
        n += 1
        if limit and n >= limit:
            break


# --- Excel/CSV houses ------------------------------------------------------ #

def _is_blank_row(row):
    """True if every cell in an openpyxl row tuple is empty.

    Guards against openpyxl's used-range extending past the real data
    (leftover formatting on deleted/never-filled rows): iter_rows() then
    yields trailing all-None rows that aren't real data. Confirmed on
    "Wermuth SA._14.03.2015" (657 real rows, 341 trailing blanks) and
    "Wermuth SA._06.06.2015" (786 real, 208 blanks) — without this guard
    they become fully-NULL lots.
    """
    return all(v is None or str(v).strip() == "" for v in row)


def load_wermuth(b, limit):
    path = os.path.join(REPO, "VinoImporter", "validatedOutput",
                        "vinoStagingFile2015-2008.xlsx")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    b.set_source(path)
    n = 0
    for ws in wb.worksheets:
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", ws.title)
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue
        header = [str(c) if c is not None else "" for c in all_rows[0]]
        event = None
        lots = []
        for row in all_rows[1:]:
            if _is_blank_row(row):
                continue
            rec = dict(zip(header, row))
            # Sheets end with a "Total: <sum of hammer prices>" row: no
            # lot_no/name/quantity, just a price. It's not a lot — skip it
            # so it can't double the auction's apparent total if anything
            # ever sums hammer_price directly over `lots`.
            if not str(_v(rec, "name") or "").strip():
                continue
            if event is None:
                ev = _v(rec, "eventIdentifier")
                if ev and str(ev).strip() not in ("", "null", "None"):
                    event = str(ev)
            lots.append(rec)
        a_id = b.add_auction("wermuth-sa", event or ws.title, ws.title,
                             date, "CHF", "HAMMER")
        for rec in lots:
            rp = _v(rec, "realizedPrice")
            b.add_lot(a_id, {
                "lot_no": str(_v(rec, "providerOfferingId")),
                "wine": _v(rec, "name"),
                "classification": _clean(_v(rec, "producer")),
                "region": _clean(_v(rec, "region")),
                "vintage": to_int(_v(rec, "vintage")),
                "quantity": to_int(_v(rec, "noOfBottles")),
                "bottle_size_dl": to_float(_v(rec, "deciliters")),
                "estimate_low": to_float(_v(rec, "priceMin")),
                "estimate_high": to_float(_v(rec, "priceMax")),
                "hammer_price": to_float(rp),
                "price_basis": "HAMMER", "currency": "CHF",
                "sold": 1 if rp not in (None, "", "null", "None") else 0,
                "is_ohk": _to_bool(_v(rec, "isOHK")),
                "note": _clean(_v(rec, "note")),
            })
        n += 1
        if limit and n >= limit:
            break


def _v(rec, key):
    """Header-tolerant field access."""
    if key in rec:
        return rec[key]
    for k in rec:
        if k and k.strip().lower() == key.strip().lower():
            return rec[k]
    return None


def _clean(v):
    """Normalize 'null'/'none' strings and blanks to None."""
    if v is None:
        return None
    s = str(v).strip().lower()
    return None if s in ("", "null", "none") else v


def _to_bool(v):
    """Normalize a boolean-ish value ('true'/'false', 1/0) to 1/0/None."""
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ("true", "1", "yes"):
        return 1
    if s in ("false", "0", "no", ""):
        return 0
    return None


def load_steinfels(b, limit):
    base = os.path.join(REPO, "priceData", "import", "steinfels", "prepared")
    files = sorted(glob.glob(os.path.join(base, "**", "results_*.xlsx"),
                             recursive=True))
    n = 0
    for f in files:
        wb = openpyxl.load_workbook(f, read_only=True, data_only=True)
        b.set_source(f)
        if "Wines" not in wb.sheetnames:
            continue
        ws = wb["Wines"]
        aid = os.path.basename(f).replace(".xlsx", "").replace("results_", "")
        year = None
        # year from path (e.g. .../2002/results_315.xlsx)
        m = re.search(r"/prepared/(\d{4})/", f)
        if m:
            year = int(m.group(1))
        a_id = b.add_auction("steinfels", aid, aid,
                             f"{year}-01-01" if year else None, "CHF", "HAMMER")
        header = None
        for i, row in enumerate(ws.iter_rows(values_only=True)):
            if i == 0:
                header = [str(c) if c is not None else "" for c in row]
                continue
            rec = dict(zip(header, row))
            b.add_lot(a_id, {
                "lot_no": str(_v(rec, "Lot")),
                "wine": _v(rec, "Wine"),
                "producer": _clean(_v(rec, "Producer")),
                "region": _clean(_v(rec, "Region")),
                "vintage": to_int(_v(rec, "Year")),
                "quantity": to_int(_v(rec, "Quantity")),
                "bottle_size_dl": to_float(_v(rec, "Unit_DL")),
                "hammer_price": to_float(_v(rec, "Price_CHF")),
                "price_basis": "HAMMER", "currency": "CHF",
            })
        n += 1
        if limit and n >= limit:
            break
    # The Alt-XLSX (2002-03) and API-JSON (current catalogs) are disjunct
    # auction-id namespaces, so both are loaded into the same "steinfels"
    # provider without collision.
    remaining = None if limit is None else limit - n
    _load_weinauktion_json(b, "steinfels", remaining)


def load_steinfels_staging(b, limit):
    """Steinfels staging workbook (16-col normalized structure, 2 events)."""
    path = os.path.join(REPO, "data", "vinoStagingFileSteinfels.xlsx")
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    b.set_source(path)
    n = 0
    for ws in wb.worksheets:
        if ws.title == "nonRecordLines":
            continue
        all_rows = list(ws.iter_rows(values_only=True))
        if not all_rows:
            continue
        header = [str(c) if c is not None else "" for c in all_rows[0]]
        m = re.search(r"(\d{2})\.(\d{2})\.(\d{4})", ws.title)
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
        event = None
        lots = []
        for row in all_rows[1:]:
            if _is_blank_row(row):
                continue
            rec = dict(zip(header, row))
            # See load_wermuth: a trailing "Total" row with a price but no
            # name/lot_no isn't a lot.
            if not str(_v(rec, "name") or "").strip():
                continue
            if event is None:
                ev = _v(rec, "eventIdentifier")
                if ev and str(ev).strip() not in ("", "null", "None"):
                    event = str(ev)
            lots.append(rec)
        a_id = b.add_auction("steinfels", event or ws.title, ws.title,
                             date, "CHF", "HAMMER")
        for rec in lots:
            rp = _v(rec, "realizedPrice")
            b.add_lot(a_id, {
                "lot_no": str(_v(rec, "providerOfferingId")),
                "wine": _v(rec, "name"),
                "classification": _clean(_v(rec, "origin")),
                "region": _clean(_v(rec, "region")),
                "vintage": to_int(_v(rec, "vintage")),
                "quantity": to_int(_v(rec, "noOfBottles")),
                "bottle_size_dl": to_float(_v(rec, "deciliters")),
                "estimate_low": to_float(_v(rec, "priceMin")),
                "estimate_high": to_float(_v(rec, "priceMax")),
                "hammer_price": to_float(rp),
                "lot_date": _clean(_v(rec, "offeringDate")),
                "price_basis": "HAMMER", "currency": "CHF",
                "sold": 1 if rp not in (None, "", "null", "None", 0) else 0,
                "is_ohk": _to_bool(_v(rec, "isOHK")),
                "note": _clean(_v(rec, "note")),
            })
        n += 1
        if limit and n >= limit:
            break


def _wermuth_xlsx_dates(conn):
    """Dates already covered by ``load_wermuth`` (the 42-sheet xlsx).

    ``load_wermuth_validated`` runs after ``load_wermuth`` in ``HOUSES``, so
    this reflects the xlsx import for the current build. The xlsx and the
    validatedOutput CSVs independently digitize the same real-world Wermuth
    auctions for 2014-12 through 2015-11 (confirmed: identical lot numbers,
    wine names and hammer prices under different auction_id spellings — the
    xlsx uses its own ``eventIdentifier`` column, the CSV loader uses the
    filename). Without this check both get loaded as separate auctions,
    silently duplicating ~3,500 lots.
    """
    return {row[0] for row in conn.execute(
        "SELECT DISTINCT a.auction_date FROM auctions a"
        " JOIN providers p ON a.provider_id = p.id"
        " WHERE p.name = 'wermuth-sa'")}


def load_wermuth_validated(b, limit):
    """Wermuth validated CSV outputs (VinoImporter, 2014-2018, no header).

    Semicolon-separated, 10 or 11 columns. 11 columns carry an ``origin``
    (classification) at index 2; 10 columns put ``producer`` there (usually
    "null"). Filename encodes the event date: output_WermuthSA_DDMMYYYY.csv.

    Skips any date already covered by ``load_wermuth`` (see
    ``_wermuth_xlsx_dates``) — purely additive for the 2016-2018 events the
    xlsx doesn't have.
    """
    base = os.path.join(REPO, "VinoImporter", "validatedOutput")
    files = sorted(glob.glob(os.path.join(base, "output_WermuthSA_*.csv")))
    xlsx_dates = _wermuth_xlsx_dates(b.conn)
    n = skipped = 0
    for f in files:
        m = re.search(r"(\d{2})(\d{2})(\d{4})", os.path.basename(f))
        date = f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None
        if date is not None and date in xlsx_dates:
            skipped += 1
            continue
        event = os.path.basename(f).replace("output_WermuthSA_", "").replace(
            ".csv", "")
        with open(f, encoding="utf-8") as fh:
            rows = list(csv.reader(fh, delimiter=";"))
        if not rows:
            continue
        b.set_source(f)
        a_id = b.add_auction("wermuth-sa", event, event, date, "CHF", "HAMMER")
        for row in rows:
            if len(row) < 10:
                continue
            has_origin = len(row) >= 11 and str(row[2]).strip() not in (
                "", "null", "None")
            off = 1 if has_origin else 0
            rp = to_float(row[9 + off])
            b.add_lot(a_id, {
                "lot_no": str(row[0]),
                "wine": row[1],
                "classification": _clean(row[2]) if has_origin else None,
                "vintage": to_int(row[3 + off]),
                "quantity": to_int(row[4 + off]),
                "bottle_size_dl": to_float(row[5 + off]),
                "is_ohk": _to_bool(row[6 + off]),
                "estimate_low": to_float(row[7 + off]),
                "estimate_high": to_float(row[8 + off]),
                "hammer_price": rp,
                "lot_date": date,
                "price_basis": "HAMMER", "currency": "CHF",
                "sold": 1 if rp not in (None, "", "null", "None", 0) else 0,
            })
        n += 1
        if limit and n >= limit:
            break
    if skipped:
        print(f"  wermuth-validated: skipped {skipped} file(s) already"
              f" covered by the xlsx import")


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

HOUSES = [
    ("baghera", load_baghera),
    ("hdh", load_hdh),
    ("winefields", load_winefields),
    ("besch-cannes", load_beschcannes),
    ("langtons", load_langtons),
    ("sothebys", load_sothebys),
    ("christies", load_christies),
    ("zacky", load_zacky),
    ("finarte", load_finarte),
    ("dorotheum", load_dorotheum),
    ("pandolfini", load_pandolfini),
    ("koppe", load_koppe),
    ("dobiaschofsky", load_dobiaschofsky),
    ("munich-wine-company", load_munich_wine_company),
    ("winebarrel", load_winebarrel),
    ("idealwine", load_idealwine),
    ("weinauktionator", load_weinauktionator),
    ("wermuth-sa", load_wermuth),
    ("wermuth-validated", load_wermuth_validated),
    ("steinfels", load_steinfels),
    ("steinfels-staging", load_steinfels_staging),
    ("weinboerse", load_weinboerse),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--only", type=str, default=None,
                    help="comma-separated house names to include")
    ap.add_argument("--skip-resolution", action="store_true",
                    help="load raw lots only, skip Stufe 2 resolution")
    args = ap.parse_args()

    if args.dry_run:
        conn = sqlite3.connect(":memory:")
        conn.execute("PRAGMA foreign_keys = ON")
        _build(conn, args)
        return

    lock_path = os.path.join(SCRIPT_DIR, ".wine-db-build.lock")
    lock_fd = _acquire_lock(lock_path)
    if lock_fd is None:
        print("Build already running (lock held).", file=sys.stderr)
        sys.exit(1)
    tmp_path = f"{DB_PATH}.tmp.{os.getpid()}"
    try:
        conn = sqlite3.connect(tmp_path)
        conn.execute("PRAGMA foreign_keys = ON")
        _build(conn, args)
        _validate_gates(conn)
        conn.commit()
        conn.close()
        os.replace(tmp_path, DB_PATH)
        print(f"published: {DB_PATH}")
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    finally:
        os.close(lock_fd)
        if os.path.exists(lock_path):
            os.remove(lock_path)


def _build(conn, args):
    conn.executescript(SCHEMA)
    b = Builder(conn)

    totals = {}
    houses = HOUSES
    if args.only:
        wanted = {h.strip() for h in args.only.split(",") if h.strip()}
        houses = [(n, f) for n, f in HOUSES if n in wanted]
    for name, fn in houses:
        before = conn.execute("SELECT count(*) FROM lots").fetchone()[0]
        try:
            fn(b, args.limit)
        except Exception as e:
            print(f"ERROR {name}: {type(e).__name__}: {e}", file=sys.stderr)
            raise
        after = conn.execute("SELECT count(*) FROM lots").fetchone()[0]
        totals[name] = after - before
        print(f"  {name:22} +{after - before} lots")

    na = conn.execute("SELECT count(*) FROM auctions").fetchone()[0]
    nl = conn.execute("SELECT count(*) FROM lots").fetchone()[0]
    np_ = conn.execute("SELECT count(*) FROM providers").fetchone()[0]
    print(f"\nproviders={np_} auctions={na} lots={nl}")

    _annotate_fx(conn)
    _apply_premium_policy(conn)
    _apply_tax(conn)
    _fill_lot_date(conn)

    if not args.skip_resolution:
        from build_wines import run as resolve_wines
        resolve_wines(conn)

    _record_build_metadata(conn)


# Legal euro fix rates for pre-euro currencies (D3): 1 EUR = rate units.
_FX_FIX = {
    "NLG": 2.20371,
}


def _annotate_fx(conn):
    """Annotate historical currencies with their legal fix rate (D3).

    Raw currency is kept; ``fx_rate`` (units per 1 EUR) and
    ``fx_target_currency`` are stored so FX/arbitrage logic can convert.
    """
    for currency, rate in _FX_FIX.items():
        conn.execute(
            "UPDATE lots SET fx_rate = ?, fx_target_currency = 'EUR'"
            " WHERE currency = ?", (rate, currency))


# Buyer's premium policy per house. ``rate`` = flat premium fraction of the
# hammer; ``fees`` = flat per-lot fee in the house currency.
#
# Approximation (documented, not exact): tiered rates are flattened to their
# first tier, and time-varying rates (langtons 16.5%->18%, winefields
# 22%->24%) use the current rate for all lots — a temporal policy would be a
# follow-up. Houses not listed: include the premium in their recorded price
# (pandolfini, zacky, hdh), are a cote/valuation price rather than an auction
# (idealwine), or are a consignment service with a seller-side fee rather than
# a buyer's premium (winebarrel). Source: docs/premium-policy.md.
PREMIUM_POLICY = {
    "sothebys": {"rate": 0.25},
    "langtons": {"rate": 0.18},
    "dorotheum": {"rate": 0.25},
    "winefields": {"rate": 0.24},
    "baghera": {"rate": 0.22},
    "steinfels": {"rate": 0.12, "fees": 10.0},
    "finarte": {"rate": 0.23},
    "weinboerse": {"rate": 0.15, "fees": 10.0},
    "koppe": {"rate": 0.10, "fees": 5.0},
    "weinauktionator": {"rate": 0.15},
    "dobiaschofsky": {"rate": 0.25},
    "wermuth-sa": {"rate": 0.10, "fees": 8.0},
    "besch-cannes": {"rate": 0.24},
    "munich-wine-company": {"rate": 0.15, "fees": 5.0},
}


def _apply_premium_policy(conn):
    """Derive buyer_premium/fees/total_price from the per-house premium policy.

    Applies only to hammer-price lots that do not already carry an observed
    buyer_premium. Marks ``price_source = DERIVED`` (hammer is OBSERVED).
    """
    for provider, policy in PREMIUM_POLICY.items():
        rate = policy["rate"]
        fees = policy.get("fees")
        conn.execute(
            "UPDATE lots SET"
            " buyer_premium = ROUND(hammer_price * ?, 2),"
            " realised_price = ROUND(hammer_price * (1 + ?), 2),"
            " fees = ?,"
            " total_price = ROUND(hammer_price * (1 + ?) + COALESCE(?, 0), 2),"
            " price_source = 'DERIVED'"
            " WHERE hammer_price IS NOT NULL AND buyer_premium IS NULL"
            " AND price_basis = 'HAMMER'"
            " AND auction_id IN (SELECT id FROM auctions WHERE provider_id ="
            " (SELECT id FROM providers WHERE name = ?))",
            (rate, rate, fees, rate, fees, provider))


_DMY_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{4})$")


def _normalize_lot_date(conn):
    """Rewrite ``dd.mm.yyyy`` lot dates to ISO ``yyyy-mm-dd``.

    Some fetchers (steinfels) emit German-formatted dates; string min/max and
    time-series work need a single ISO format. Unparseable values (e.g.
    31.02.2020) are left untouched and counted. Returns ``(converted, invalid)``.
    """
    converted = invalid = 0
    rows = conn.execute(
        "SELECT DISTINCT lot_date FROM lots WHERE lot_date LIKE '__.__.____'"
    ).fetchall()
    for (raw,) in rows:
        m = _DMY_DATE.match(raw)
        try:
            iso = datetime.date(int(m.group(3)), int(m.group(2)),
                                int(m.group(1))).isoformat()
        except (AttributeError, ValueError):
            invalid += conn.execute(
                "SELECT COUNT(*) FROM lots WHERE lot_date = ?", (raw,)
            ).fetchone()[0]
            continue
        converted += conn.execute(
            "UPDATE lots SET lot_date = ? WHERE lot_date = ?",
            (iso, raw)).rowcount
    if invalid:
        print(f"WARN: {invalid} lots with unparseable dd.mm.yyyy lot_date")
    return converted, invalid


def _fill_lot_date(conn):
    """Normalize lot_date to ISO, then backfill from auctions.auction_date (D3).

    Only fills NULL lot_date; existing values are never overwritten (apart
    from the format normalization above).
    """
    _normalize_lot_date(conn)
    conn.execute(
        "UPDATE lots SET lot_date ="
        " (SELECT auction_date FROM auctions WHERE auctions.id = lots.auction_id)"
        " WHERE lot_date IS NULL")


# VAT/USt on the buyer's premium for houses with a clearly documented legal
# rate. ``tax_amount`` is derived as a fraction of the buyer's premium (not the
# hammer). Houses whose premium already includes VAT (finarte, besch-cannes,
# dorotheum, baghera) or whose rate is not numerically documented (sothebys,
# langtons, christies) are intentionally absent.
TAX_POLICY = {
    "winefields": 0.21,
    "steinfels": 0.081,
    "weinboerse": 0.081,
    "wermuth-sa": 0.081,
    "dobiaschofsky": 0.081,
    "koppe": 0.19,
    "weinauktionator": 0.19,
    "munich-wine-company": 0.19,
}


def _apply_tax(conn):
    """Derive tax_amount (VAT/USt on the buyer's premium) per TAX_POLICY.

    Applies only to lots that already carry a buyer_premium (derived by
    ``_apply_premium_policy`` or observed). ``total_price`` is extended by the
    tax amount: total_price = realised + fees + tax.
    """
    for provider, rate in TAX_POLICY.items():
        conn.execute(
            "UPDATE lots SET"
            " tax_amount = ROUND(buyer_premium * ?, 2),"
            " total_price = total_price + ROUND(buyer_premium * ?, 2)"
            " WHERE buyer_premium IS NOT NULL"
            " AND auction_id IN (SELECT id FROM auctions WHERE provider_id ="
            " (SELECT id FROM providers WHERE name = ?))",
            (rate, rate, provider))


def _acquire_lock(lock_path):
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        os.write(fd, str(os.getpid()).encode())
        return fd
    except FileExistsError:
        return None


def _validate_gates(conn):
    problems = []
    ic = conn.execute("PRAGMA integrity_check").fetchone()
    if ic and ic[0] != "ok":
        problems.append(f"integrity_check: {ic[0]}")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk:
        problems.append(f"foreign_key_check: {len(fk)} violations")
    mixed_ref = conn.execute(
        "SELECT count(*) FROM lots WHERE lot_kind='MIXED'"
        " AND wine_ref_id IS NOT NULL").fetchone()[0]
    if mixed_ref:
        problems.append(f"mixed lots with wine_ref_id: {mixed_ref}")
    conflict_final = conn.execute(
        "SELECT count(*) FROM lots WHERE vintage_status='CONFLICT'"
        " AND vintage_final IS NOT NULL").fetchone()[0]
    if conflict_final:
        problems.append(f"conflict lots with vintage_final: {conflict_final}")
    if problems:
        raise RuntimeError("validation gates failed: " + "; ".join(problems))


def _record_build_metadata(conn):
    import hashlib
    import platform

    from wine_resolution import (LOADER_VERSION, NORMALIZER_VERSION,
                                 RESOLVER_VERSION)

    files = sorted(glob.glob(os.path.join(ARCHIVE, "**", "*.json"),
                             recursive=True))
    files += sorted(glob.glob(os.path.join(REPO, "VinoImporter",
                                           "validatedOutput", "*.xlsx")))
    files += sorted(glob.glob(os.path.join(REPO, "priceData", "import",
                                           "steinfels", "prepared", "**",
                                           "*.xlsx"), recursive=True))
    files = [f for f in files if "/IDealwine/" not in f
             and "wines_directory" not in f and "auctions_directory" not in f]

    build_id = hashlib.sha256(
        repr(sorted(files)).encode("utf-8")).hexdigest()[:32]
    entries = []
    for f in files:
        with open(f, "rb") as fh:
            sha = hashlib.sha256(fh.read()).hexdigest()
        size = os.path.getsize(f)
        entries.append((os.path.relpath(f, ARCHIVE), sha, size))
    entries.sort()
    manifest_sha = hashlib.sha256(repr(entries).encode("utf-8")).hexdigest()

    now = __import__("datetime").datetime.now().isoformat()
    conn.execute(
        "INSERT INTO builds(id, started_at, completed_at,"
        " input_manifest_sha256, loader_version, normalizer_version,"
        " resolver_version, python_version, sqlite_version, status)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (build_id, now, now, manifest_sha, LOADER_VERSION, NORMALIZER_VERSION,
         RESOLVER_VERSION, platform.python_version(),
         sqlite3.sqlite_version, "OK"))
    for rel, sha, size in entries:
        conn.execute(
            "INSERT INTO build_inputs(build_id, source_file,"
            " source_file_sha256, file_size) VALUES (?,?,?,?)",
            (build_id, rel, sha, size))


if __name__ == "__main__":
    main()
