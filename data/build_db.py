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
import bisect
import csv
import datetime
import glob
import json
import os
import re
import hashlib
import sqlite3
import subprocess
import sys
import zipfile

import openpyxl
from bs4 import BeautifulSoup

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
  fx_rate_date        TEXT,
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

-- Market FX rates (EODHD, cached by fetch_fx.py): units of `currency` per
-- 1 EUR on `date` (calendar days with a quote only; consumers look up as-of).
CREATE TABLE fx_rates (
  currency TEXT NOT NULL,
  date     TEXT NOT NULL CHECK (date GLOB '[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]'),
  per_eur  REAL NOT NULL CHECK (per_eur > 0 AND per_eur < 1e6),
  source   TEXT NOT NULL,
  PRIMARY KEY (currency, date)
) WITHOUT ROWID;

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


_CHRISTIES_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5,
    "june": 6, "july": 7, "august": 8, "september": 9, "october": 10,
    "november": 11, "december": 12,
    # A handful of files carry German month names instead of English.
    "januar": 1, "februar": 2, "märz": 3, "mai": 5, "juni": 6, "juli": 7,
    "oktober": 10, "dezember": 12,
}
# "13 December" or a multi-day sale "12 – 13 December" (take the first day).
_CHRISTIES_DATE_DISPLAY_RE = re.compile(
    r"^(\d{1,2})(?:\s*[-–]\s*\d{1,2})?\s+([A-Za-zÀ-ÿ]+)$")
# Two archive-wide, always-the-same typos in the older scrape's location
# field (fixed in the richer re-scrape, but not every auction has one).
_CHRISTIES_LOCATION_FIX = {"NewYork": "New York", "HongKong": "Hong Kong"}


def _christies_parse_date_display(dd, year):
    if not dd or not year:
        return None
    m = _CHRISTIES_DATE_DISPLAY_RE.match(dd.strip())
    if not m:
        return None
    month = _CHRISTIES_MONTHS.get(m.group(2).lower())
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(m.group(1)):02d}"


def _christies_directory():
    """event_id -> directory entry, from the one file excluded from the
    main glob (it's an index, not an auction) -- `start_date` there is a
    clean ISO timestamp for ~97% of auctions, more reliable than parsing
    `date_display` text out of each auction's own file."""
    path = os.path.join(ARCHIVE, "Christies", "wine_auctions_directory.json")
    if not os.path.exists(path):
        return {}
    return {str(e.get("event_id")): e for e in load_json(path)}


_NO_LETTER = re.compile(r"[A-Za-zÀ-ÿ]")


def _resolve_christies_ditto_lots(lots):
    """Christie's own historic catalogs use ditto marks ("same as the lot
    above") instead of reprinting a repeated wine name across consecutive
    lots; the scrape kept the literal ditto glyphs as the lot's title and
    description instead of resolving them. Confirmed on auction 10025
    (2000/01_Januar): lot 11 is "Armagnac--Vintage 1982" (Chateau de
    Lacaze, 1 dozen bottles); lots 12-14 are each literally "1 ^,,^^,,^",
    "1 ^,,^^,,^", "1 ^,,^^,,^" -- their own estimate/hammer price, but no
    wine text at all. This is the single largest cause of unresolved
    SINGLE lots project-wide: 8,549 of 8,713 lots with lot_kind='SINGLE'
    and wine_ref_id IS NULL are christies, and 8,549 of those (100%) have
    a title with zero letters in it (``^,,^``, ``''``, or mixes thereof --
    the archive uses several ditto glyph styles). No real wine name is
    letter-free, so that's the detection rule -- not a guess at any one
    exact symbol sequence. Each ditto lot inherits title+description from
    the nearest *preceding* non-ditto lot in the same auction (lots
    appear in ascending lot_number order in the raw file); a ditto lot
    never becomes the new "last real" reference for lots after it. A
    ditto run with no preceding real lot (none observed, but possible at
    the very start of a sale) is left untouched -- same as before this
    fix, not a regression."""
    last_title = last_desc = None
    out = []
    for lot in lots:
        title = lot.get("title")
        # An empty title (not just a ditto-glyph one) is the same "no wine
        # text" case -- confirmed on auction 5689 (1998/02_Februar): lot
        # 168 "Cote de Beaune. Ramonet", lot 169 title="", description
        # "Above 4 bottles per lot" (a continuation sub-lot, not a
        # withdrawn/blank lot).
        is_ditto = not title or not _NO_LETTER.search(title)
        if is_ditto:
            if last_title is not None:
                lot = dict(lot, title=last_title, description=last_desc)
        else:
            last_title = title
            last_desc = lot.get("description")
        out.append(lot)
    return out


def load_christies(b, limit):
    directory = _christies_directory()
    # The archive keeps BOTH the project's original flat-path scrape and
    # a later, richer re-scrape of the same sale organized into a year/
    # month subfolder (exact date, sale_total, full lot descriptions) --
    # kept side by side on purpose (re-scraping risks a Cloudflare block,
    # so old scrapes are never deleted), not two different auctions.
    # Confirmed on "20043": identical 1074 lots, same prices, richer
    # metadata only in the year/month copy. Group by sale id, keep one
    # file per id, preferring the subfolder path when both exist.
    by_id = {}
    for f in _json_files("Christies"):
        d = load_json(f)
        a = d.get("auction", {})
        aid = str(a.get("event_id") or a.get("sale_id"))
        has_subdir = re.search(r"/Christies/\d{4}/", f) is not None
        prev = by_id.get(aid)
        if prev is None or (has_subdir and not prev[1]):
            by_id[aid] = (f, has_subdir, d)

    n = 0
    for aid in sorted(by_id):
        f, _, d = by_id[aid]
        b.set_source(f)
        a = d.get("auction", {})
        dir_entry = directory.get(aid, {})
        date = None
        start = dir_entry.get("start_date")
        if start:
            date = start[:10]
        if not date:
            date = _christies_parse_date_display(
                a.get("date_display") or dir_entry.get("date_display"),
                a.get("year") or dir_entry.get("year"))
        if not date:
            date = ym_date(a.get("year"), a.get("month"))
        location = a.get("location") or dir_entry.get("location")
        location = _CHRISTIES_LOCATION_FIX.get(location, location)
        a_id = b.add_auction(
            "christies", aid, a.get("title"), date, None, "HAMMER",
            a.get("landing_url"), location=location)
        for lot in _resolve_christies_ditto_lots(d.get("lots", [])):
            sold = 1 if (lot.get("price_realised") and
                         not lot.get("lot_withdrawn")) else 0
            price = to_float(lot.get("price_realised"))
            currency = lot.get("currency")
            # Christie's "price realised" is gross (incl. buyer's
            # premium); back out the net hammer and keep the gross as
            # realised_price. Historic NLG (pre-euro Amsterdam) lots used
            # 20.825%, not the 25% wine rate -- 6,188 lots carry currency
            # 'NLG' and were silently getting the wrong rate.
            premium_rate = 1.20825 if currency == "NLG" else 1.25
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_number")),
                "wine": lot.get("title"),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                "hammer_price": round(price / premium_rate, 2)
                if price is not None else None,
                "realised_price": price,
                "price_basis": "HAMMER",
                "currency": currency,
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
        # Two scrape generations, both confirmed real: an older wayback
        # archive using Zachys' own small-integer auctionid (235 files,
        # id 19-287), and a later, richer "structured" scrape that
        # carries its own sale_no (e.g. "2409i") plus a small sequential
        # id (97 files, id 56-169) -- that id is an artifact of the newer
        # scrape, not a Zachys auction id, and collides with an unrelated
        # wayback-generation sale for 87 of the 97 files (e.g. id "72" is
        # both "zCollections, June 9-14th" 2020, 25 lots, wayback, and
        # "zCollections, New York, August 19 - September 1" 2024, 957
        # lots, structured) -- both got merged into one auction record.
        # sale_no is present, unique, and collision-free with every
        # wayback id across the whole archive; prefer it when present.
        aid = str(a.get("sale_no") or a.get("id"))
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
        for idx, lot in enumerate(d.get("lots", []), start=1):
            # The raw lot has no lot_no/position field at all (confirmed
            # across every archived file) -- str(None) made every lot in
            # an auction share the literal lot_no "None", which collided
            # as a false "duplicate" whenever two genuinely different
            # lots happened to share the same wine text and price. The
            # list position is stable and unique per auction; it's not
            # the real catalog number, but it's a real identifier where
            # none existed before.
            lot_no = lot.get("lot_no")
            b.add_lot(a_id, {
                "lot_no": str(lot_no) if lot_no is not None else str(idx),
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


def _load_weinauktion_json(b, provider, limit, aid_prefix=""):
    """Load the weinauktion-platform API JSON (steinfels / weinboerse).

    Only matches ``run_ingest.py``-fetched files (``{auction, lots}``,
    both always present per ``orchestrate._is_valid``) -- NOT this house's
    own raw paginated export (``@related``/``items``), which has neither
    key: ``d.get("auction", {})`` would silently be ``{}``, creating one
    phantom "None"-id auction per file instead of 0 (confirmed: this is
    exactly how the original, broken weinboerse loader produced its
    "1 auction / 0 lots" symptom).

    ``aid_prefix`` disambiguates the platform's own numeric auction id
    from an unrelated id namespace already used for this provider --
    steinfels' 2002-03 XLSX batch is numbered by sequential *file*
    number (e.g. "321"), not a platform auction id, and the platform's
    own ids run low enough (251 for a 2023 sale) to collide with it by
    pure coincidence (confirmed real case: DB auction id 6 ended up with
    both "Château Angélus" from the XLSX and an unrelated "Château de
    Bel-Air" lot from the API under the same auction_id "321", both
    claiming lot_no "1"). weinboerse has no such second namespace, so it
    passes none.

    Known residual risk (senior review, not fixed -- needs real-archive
    verification before touching it, not a guess): for steinfels, this
    function's ``a.get("id")`` is the live fetcher's own ``cat_id``
    (catalog id -- see ``ingest/fetchers/weinauktion.py``'s ``discover``:
    ``ref.auction_id = str(cat_id)``), while
    ``_load_steinfels_resultfile_json`` resolves ids all the way to the
    platform's true parent ``auctionId``. Both get the same "api-"
    prefix, so a catalog id could in principle still collide with an
    unrelated sale's true auction id. Checked against the live production
    DB after this session's rebuild: every "api-*" steinfels auction_id
    currently has exactly one coherent title and no duplicate lot_no --
    zero actual collisions today -- but that is not a guarantee against a
    future one.
    """
    n = 0
    for f in _json_files(provider):
        d = load_json(f)
        if not d.get("auction") or not d.get("lots"):
            continue
        b.set_source(f)
        a = d.get("auction", {})
        aid = aid_prefix + str(a.get("id"))
        a_id = b.add_auction(provider, aid, a.get("name"),
                             parse_date(a.get("date")),
                             a.get("currency") or "CHF", "HAMMER")
        for lot in d.get("lots", []):
            sold = bool(lot.get("sold"))
            b.add_lot(a_id, {
                "lot_no": str(lot.get("lot_no")),
                "wine": lot.get("wine"),
                "vintage": to_int(lot.get("vintage")),
                "estimate_low": to_float(lot.get("estimate_low")),
                "estimate_high": to_float(lot.get("estimate_high")),
                "hammer_price": to_float(lot.get("hammer_price")),
                "price_basis": "HAMMER" if sold else "UNKNOWN",
                "currency": lot.get("currency") or "CHF",
                "sold": 1 if sold else 0,
            })
        n += 1
        if limit and n >= limit:
            break
    return n


# Quantity line: "<N> [<frac> ]<unit word>[ <N.N>L]". The fraction (e.g.
# "12 3/8 Flaschen") is a bottle-SIZE modifier (3/8 of a liter = a 0.375L
# half-bottle), not a quantity modifier; the trailing "<N>L"/"<N.N>L" (e.g.
# "1 Impérial 6L", "1 Jeroboam 5L") is an explicit size that overrides the
# named-format default below -- large-format names are not fixed volumes
# across houses/regions (a Bordeaux vs. Champagne Jeroboam differ), so the
# explicit liters, when given, is authoritative over the name alone.
_WB_QTY_LINE = re.compile(
    r"^(\d+)\s+(?:(\d+)/(\d+)\s+)?([A-Za-zÀ-ÿ.]+)"
    r"(?:\s+(\d+(?:[.,]\d+)?)\s*L?)?$", re.IGNORECASE)
_WB_NAMED_DL = {
    "flasche": 7.5, "flaschen": 7.5, "fl": 7.5, "halbliter": 5.0,
    "magnum": 15.0, "mg": 15.0, "doppelmagnum": 30.0, "dmg": 30.0,
    "jeroboam": 45.0, "imperiale": 60.0, "impériale": 60.0,
    "imperial": 60.0, "impérial": 60.0, "bal": 120.0, "balthazar": 120.0,
    "div": None,
}
_WB_JAHRGANG = re.compile(r"^Jahrgang:\s*(.+)$", re.IGNORECASE)
_WB_YEAR = re.compile(r"^\d{4}$")
# Case-sensitive on purpose: the source always writes these markers
# uppercase, and case-insensitive matching turns "Pays d'Oc" (Languedoc)
# into a false OHK hit ("Oc" at the end, both \b boundaries hold).
_WB_OHK = re.compile(
    r"(?:,|\s+in)?\s*(?:\d+er\s+)?\b(?:OHK|OC|OWC|CBO)\b\.?"
    r"(?:\s*\([^)]*\))?\s*$")
_WB_OHK_PREFIX = re.compile(
    r"^(?:\d+er\s+)?\b(?:OHK|OC|OWC|CBO)\b\.?\s*,?\s*(.*)$")
_WB_MULTI_WINE = re.compile(r"(\d+)x\s+([^,]+?)(?=,|$)")
_WB_SCORE = re.compile(r"^RP\s*[\d.+\-]+$", re.IGNORECASE)
_WB_CM = re.compile(r"^\d+(?:[.,]\d+)?\s*cm$", re.IGNORECASE)
# Condition/fill-level shorthand that mimics the "<N>x <wine>" mixed-wine
# pattern (e.g. "4x befleckt, 1x defekt" = "4 bottles stained, 1 defective
# label", not two different wines) -- excluded from the mixed-lot count so
# a condition-heavy single-wine lot isn't mistaken for a multi-wine one.
_WB_CONDITION_WORDS = {
    "befleckt", "defekt", "geschürft", "angegraut", "kellergrau",
    "zerknittert", "oxidiert", "verfärbt", "beschädigt", "hs", "ts", "vts",
    "ms", "in", "hf", "etikett", "etiketten", "kapsel", "kapseln",
}


_WB_LEADING_SIZE = re.compile(r"^\d+(?:[.,]\d+)?\s*L\s+", re.IGNORECASE)


def _wb_is_real_subwine(group):
    # A sub-item is sometimes "<N>x <size>L <Wine>, ..." (e.g. "1x 0.75L
    # Pinot Noir Monolith, Obrecht") -- strip the size before judging
    # whether what follows looks like a real wine name.
    g = _WB_LEADING_SIZE.sub("", group.strip())
    if not g or not g[0].isupper():
        return False
    first_word = re.split(r"[\s/]", g, maxsplit=1)[0].lower().rstrip(".,")
    return first_word not in _WB_CONDITION_WORDS
# "Mixed Lots / MIXED LOT", "WinePROOF / WinePROOF", any "CHOIX DE
# <region>" (a themed assortment, e.g. "CHOIX DE BORDEAUX") and its German
# equivalent "AUSWAHL <region>" (e.g. "AUSWAHL GRAUBÜNDEN") are not real
# producers -- the house's own catalog category or a third-party
# authentication-service label, repeated as a placeholder where no single
# producer applies (a genuine multi-wine assortment, or the real producer
# is embedded in the wine text itself, e.g. "DRC, Echézeaux Grand Cru, mit
# GA Safety Tag...").
_WB_PLACEHOLDER_PRODUCER = re.compile(
    r"^(MIXED LOT|WINEPROOF|CHOIX DE .+|AUSWAHL\b.*)$", re.IGNORECASE)


def _wb_strip_html(s):
    return re.sub(r"<[^>]+>", " ", s).strip()


def _wb_parse_qty_line(seg):
    """'<N> [<frac> ]<unit>[ <N>L]' -> (quantity, bottle_size_dl) or None."""
    m = _WB_QTY_LINE.match(seg)
    if not m:
        return None
    qty_s, frac_num, frac_den, unit, liters = m.groups()
    quantity = int(qty_s)
    if frac_num:
        dl = (int(frac_num) / int(frac_den)) * 10
    elif liters:
        dl = float(liters.replace(",", ".")) * 10
    else:
        dl = _WB_NAMED_DL.get(unit.lower().rstrip("."))
    return quantity, dl


def _wb_parse_description(desc, key, errors):
    """Parse a Weinbörse lot description into structured fields.

    Two source formats share this field, distinguished by their line
    separator (confirmed empirically: mutually exclusive except one lot
    whose internal sub-item lines borrow the other style -- harmless, both
    separators are normalized away before splitting):

    - Most lots (``<br />``): an optional '<category> / <PRODUCER>' header
      line, the wine name (optional trailing ', OHK' / ', 6er OC' marker,
      or -- for a compound "Mixed Lots" assortment -- several such lines
      joined), an optional 'Jahrgang: <year>' line (absent, or a
      mixed-vintage list like "1x 2011, 6x 2012..." for a same-wine
      multi-vintage lot), a '<N> <unit>' quantity line, then a
      'Schätzpreis: ...' line duplicating the structured
      basePrice/upperBasePrice fields.
    - A Champagne-catalog export (bare ``<br>``, no '<category> /' line at
      all): producer alone as the first line, wine name, a *bare* 4-digit
      vintage (no 'Jahrgang:' prefix), the quantity line, then an optional
      trailing critic-score ('RP97') or condition note ('1.5cm', '1er OHK
      (befleckt und angegraut)').
    """
    is_bare_style = "<br />" not in (desc or "")
    segs = [_wb_strip_html(s) for s in re.split(r"<br\s*/?>", desc or "")]
    segs = [s for s in segs if s]

    producer = None
    region = None
    color = None
    if segs and " / " in segs[0]:
        # rsplit, not split: a US lot's header is "USA / Kalifornien /
        # HEITZ" (country / region / producer) -- the producer is always
        # the text after the LAST slash, not the first.
        region, producer = segs[0].rsplit(" / ", 1)
        region = region.strip() or None
        producer = producer.strip() or None
        if region:
            m_color = re.match(r"^(.*?)\s+(rot|weiss|weiß)$", region,
                                re.IGNORECASE)
            if m_color:
                region = m_color.group(1).strip() or None
                color = "Rot" if m_color.group(2).lower() == "rot" else "Weiß"
        segs = segs[1:]
    elif is_bare_style and segs:
        producer = segs[0] or None
        segs = segs[1:]

    mixed_lot = 0
    if producer and _WB_PLACEHOLDER_PRODUCER.match(producer.strip()):
        if producer.strip().upper() == "MIXED LOT":
            mixed_lot = 1
        producer = None

    vintage = None
    quantity = None
    bottle_size_dl = None
    is_ohk = False
    wine_parts = []
    for seg in segs:
        if seg.lower().startswith("schätzpreis"):
            continue
        if _WB_SCORE.match(seg) or _WB_CM.match(seg):
            continue
        if seg.lower().startswith("winebutler"):
            # A tasting-note blurb ("Winebutler: Der 2009er Château...")
            # appended after the structured fields on some bare-style
            # lots -- marketing prose, never wine-identifying data, and
            # always last, so stop collecting entirely once it starts.
            break
        m = _WB_JAHRGANG.match(seg)
        if m:
            vtext = m.group(1).strip()
            if _WB_YEAR.match(vtext):
                vintage = int(vtext)
            # else: mixed-vintage list for one wine -- not worth a
            # per-vintage split, leave vintage unset rather than guess.
            continue
        if vintage is None and _WB_YEAR.match(seg):
            vintage = int(seg)
            continue
        m = _wb_parse_qty_line(seg)
        if m:
            quantity, bottle_size_dl = m
            continue
        # OHK/OC as a condition-note PREFIX ("OHK ohne Deckel, Etikett
        # ..."), as opposed to the more common wine-name SUFFIX ("Volnay
        # 1er Champans, OC") handled below once the full name is joined.
        m = _WB_OHK_PREFIX.match(seg)
        if m:
            is_ohk = True
            rest = m.group(1).strip()
            if rest:
                wine_parts.append(rest)
            continue
        wine_parts.append(seg)

    wine_name = " ".join(wine_parts).strip()
    if not wine_name:
        # First-growth-style Bordeaux lots: the château name alone is the
        # wine, no separate wine-name line is given at all (confirmed on
        # the source: "Bordeaux rot / CHATEAU ANGELUS<br /><br />Jahrgang:
        # ...") -- fall back to the producer rather than drop a real,
        # priced lot over a formatting quirk.
        if producer:
            wine_name = producer
        else:
            errors.append(f"NO_WINE_NAME{key}: {desc!r}")
            return None

    m = _WB_OHK.search(wine_name)
    if m:
        is_ohk = True
        wine_name = wine_name[:m.start()].strip()

    if not mixed_lot:
        multi = _WB_MULTI_WINE.findall(wine_name)
        real = [g for _, g in multi if _wb_is_real_subwine(g)]
        if len(real) >= 2:
            mixed_lot = 1

    if quantity is None:
        errors.append(f"NO_QUANTITY{key}: {desc!r}")

    return {
        "wine": wine_name, "producer": producer, "vintage": vintage,
        "quantity": quantity, "bottle_size_dl": bottle_size_dl,
        "is_ohk": is_ohk, "mixed_lot": mixed_lot,
        "region": region, "color": color,
    }


def load_weinboerse(b, limit):
    """Weinbörse Zürich: paginated JSON export (20 items/page, 2020-2026).

    Not the old weinauktion-platform API shape ``_load_weinauktion_json``
    expects -- each page is ``{"@related": {auctions, catalogs, parts,
    ...}, "items": [...]}``, with an item linked to its auction via
    auctionCatalogPartId -> parts[].auctionCatalogId -> catalogs[].auctionId
    -> auctions[]. A page embeds only the slice of that graph its own items
    need, not a global directory, so this does two passes: collect the
    graph from every file first, then resolve+load items.

    Items repeat verbatim across re-scraped pages -- same
    (auctionCatalogPartId, id) key, byte-identical content every time
    (confirmed empirically: unique full-record hashes == unique keys) --
    so a seen-set dedup is required or lots would be inserted many times
    over (one key observed 71 times).
    """
    files = _json_files("Weinboerse", "**/Resultfile*.json")

    auctions, catalogs, parts = {}, {}, {}
    for f in files:
        rel = load_json(f).get("@related", {})
        for a in rel.get("auctions", []):
            auctions[a["id"]] = a
        for c in rel.get("catalogs", []):
            catalogs[c["id"]] = c
        for p in rel.get("parts", []):
            parts[p["id"]] = p
    part_to_auction = {
        pid: catalogs[p["auctionCatalogId"]]["auctionId"]
        for pid, p in parts.items() if p.get("auctionCatalogId") in catalogs
    }

    # Auctions the CI fetcher has already written as a file of its own
    # (lowercase "weinboerse/<catalog_id>.json", the ``{auction, lots}``
    # shape -- see ``_load_weinauktion_json`` below). The fetcher's catalog
    # ids do not cleanly partition from this dump's (168->167, 202->200,
    # 235->233, 236->234 collapse to the SAME auction), so without this,
    # the first CI run would double-load every auction it refetches on top
    # of the frozen historical dump. Mirrors ``_wermuth_xlsx_dates``: the
    # fresher source (here, the live fetch) wins, the frozen dump fills in
    # whatever it hasn't covered yet.
    fetched_auction_ids = set()
    for f in _json_files("weinboerse"):
        if os.path.basename(f).lower().startswith("resultfile"):
            continue
        cat_id = os.path.splitext(os.path.basename(f))[0]
        cat = catalogs.get(int(cat_id)) if cat_id.isdigit() else None
        if cat:
            fetched_auction_ids.add(cat["auctionId"])

    errors = []
    seen = set()
    auction_db_id = {}
    n = 0
    for f in files:
        d = load_json(f)
        b.set_source(f)
        for it in d.get("items", []):
            key = (it.get("auctionCatalogPartId"), it.get("id"))
            if key in seen:
                continue
            seen.add(key)
            if part_to_auction.get(key[0]) in fetched_auction_ids:
                continue

            aid = part_to_auction.get(key[0])
            a = auctions.get(aid)
            if a is None:
                errors.append(f"NO_AUCTION{key}")
                continue
            if aid not in auction_db_id:
                auction_db_id[aid] = b.add_auction(
                    "weinboerse", str(aid), a.get("title"),
                    parse_date(a.get("startDate")),
                    a.get("currency") or "CHF", "HAMMER")
            a_id = auction_db_id[aid]

            parsed = _wb_parse_description(it.get("description"), key, errors)
            if parsed is None:
                continue

            sold = 1 if it.get("state") == "sold" else 0
            b.add_lot(a_id, {
                "lot_no": str(it.get("number")),
                "source_lot_key": f"{key[0]}:{key[1]}",
                "wine": parsed["wine"], "producer": parsed["producer"],
                "vintage": parsed["vintage"], "quantity": parsed["quantity"],
                "bottle_size_dl": parsed["bottle_size_dl"],
                "region": parsed["region"], "color": parsed["color"],
                "is_ohk": 1 if parsed["is_ohk"] else 0,
                "mixed_lot": parsed["mixed_lot"] or None,
                "estimate_low": to_float(it.get("basePrice")),
                "estimate_high": to_float(it.get("upperBasePrice")),
                "hammer_price": to_float(it.get("hammerPrice")) if sold else None,
                "price_basis": "HAMMER" if sold else "UNKNOWN",
                "currency": a.get("currency") or "CHF",
                "sold": sold,
                "description": it.get("description"),
            })
        n += 1
        if limit and n >= limit:
            break

    if errors:
        print(f"WARN load_weinboerse: {len(errors)} issues"
              f" (first 5: {errors[:5]})")

    # The historical bulk dump above (this house's own paginated export,
    # "Weinboerse/**/Resultfile*.json") is a one-time, now-frozen snapshot.
    # Going forward, the CI ``WeinauktionFetcher`` (same live API, see
    # ingest/fetchers/weinauktion.py) writes NEW auctions to the lowercase
    # "weinboerse/<auction_id>.json" directory in the simpler {auction,
    # lots} shape -- a genuinely different, non-overlapping directory on a
    # case-sensitive filesystem (CI), even though the two names collide
    # into one folder locally on case-insensitive macOS. Without this
    # call, every month's newly-fetched auction would silently never load.
    remaining = None if limit is None else max(0, limit - n)
    # `_load_weinauktion_json`'s own `if limit and n >= limit` treats 0 as
    # falsy (unlimited), so a used-up budget must skip the call outright
    # rather than pass 0 through.
    if remaining is None or remaining > 0:
        _load_weinauktion_json(b, "weinboerse", remaining)


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


def _dedupe_munich_lots(lots):
    """The raw archive has two scrape artifacts, both confirmed on real
    auctions: some lots are repeated byte-for-byte verbatim (143 rows
    across the archive, e.g. auction-111.json lot "81"), and others are
    scraped twice at different auction states -- once before the sale
    closed (price_text="", hammer_price=None) and once after (both
    populated), otherwise identical (19 cases, e.g. auction-89.json lot
    "101"). Keeping one row per (lot_no, name, count_fill, description),
    preferring the copy with a populated hammer_price, fixes both without
    touching genuinely different lots that happen to share a lot_no --
    e.g. auction-65.json's "9999" catch-all (four unrelated wines) or
    auction-124.json lot "153" (two different vintages in the name
    text) keep their own key and are left alone."""
    best = {}
    order = []
    for lot in lots:
        key = (lot.get("lot_no"), lot.get("name"), lot.get("count_fill"),
               lot.get("description"))
        if key not in best:
            best[key] = lot
            order.append(key)
        elif (best[key].get("hammer_price") is None
              and lot.get("hammer_price") is not None):
            best[key] = lot
    return [best[k] for k in order]


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
        for lot in _dedupe_munich_lots(d.get("lots", [])):
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
    # Not a classic multi-lot batch-sale house: each numbered "auction" on
    # the live site (and in the CI fetcher's output below) is a single
    # wine lot, continuously consigned -- so everything lands in one
    # virtual "all" auction, same as the static dump.
    f = os.path.join(ARCHIVE, "winebarrel", "winebarrel_lots.json")
    # The live fetcher (ingest/fetchers/winebarrel.py) writes one
    # {auction, lots} file per lot, named "<auction_id>.json" -- the same
    # convention _load_weinauktion_json relies on for steinfels/
    # weinboerse.
    fetched_files = [jf for jf in _json_files("winebarrel")
                     if os.path.basename(jf) != "winebarrel_lots.json"]
    if not os.path.exists(f) and not fetched_files:
        # No archive data at all (e.g. ARCHIVE_PATH not mounted) -- don't
        # insert an empty provider/auction row for nothing.
        return

    a_id = b.add_auction("winebarrel", "all", "winebarrel", None, None, "HAMMER")
    n = 0
    seen_lot_nos = set()

    if os.path.exists(f):
        d = load_json(f)
        b.set_source(f)
        for lot in d:
            if limit and n >= limit:
                return
            lot_no = str(lot.get("auction_id"))
            seen_lot_nos.add(lot_no)
            b.add_lot(a_id, {
                "lot_no": lot_no,
                "lot_date": parse_date(lot.get("auction_end")),
                "wine": lot.get("name"), "producer": lot.get("winery"),
                "vintage": to_int(lot.get("vintage")),
                "quantity": to_int(lot.get("bottles")),
                "region": lot.get("region"),
                "hammer_price": to_float(lot.get("hammer_price")),
                "price_basis": "HAMMER",
            })
            n += 1

    # Skip any id the static dump already has, so a refetch of an
    # already-covered lot is never double-loaded.
    for jf in fetched_files:
        if limit and n >= limit:
            return
        jd = load_json(jf)
        if not jd.get("auction") or not jd.get("lots"):
            continue
        for lot in jd["lots"]:
            lot_no = str(lot.get("lot_no"))
            if lot_no in seen_lot_nos:
                continue
            seen_lot_nos.add(lot_no)
            b.set_source(jf)
            sold = bool(lot.get("sold"))
            b.add_lot(a_id, {
                "lot_no": lot_no,
                "lot_date": parse_date(lot.get("auction_end")),
                "wine": lot.get("wine"), "producer": lot.get("producer"),
                "quantity": to_int(lot.get("quantity")),
                "bottle_size_dl": to_float(lot.get("bottle_size_dl")),
                "region": lot.get("region"),
                "hammer_price": to_float(lot.get("hammer_price")),
                "sold": 1 if sold else 0,
                "currency": lot.get("currency") or "CHF",
                "price_basis": "HAMMER" if sold else "UNKNOWN",
            })
            n += 1
            if limit and n >= limit:
                return


# --- sylvies (Belgian wine auctions) ---------------------------------------- #
#
# Two disjoint sources, loaded by two separate functions sharing the
# "sylvies" provider (same pattern as load_wermuth / load_wermuth_validated):
#
# - load_sylvies_html: 6 months of 2012, archived as the site's raw HTML
#   (a zip of paginated "Resultatfile<N>.html" per month). Full fidelity --
#   every lot's complete field set, including every wine in a mixed lot.
# - load_sylvies_txt: every other month 2012-2026, archived only as the
#   STDOUT of running sylviesParser.py/sylviesParser2024.py live against
#   the site (the raw HTML itself was never saved). That scraper has two
#   confirmed bugs baked permanently into this capture (the original HTML
#   is gone, so neither is recoverable here):
#     1. `result_element.find_next("p")` is unscoped: for an unsold lot
#        (no <p> after "Result" in the DOM, just a bare text node), it
#        skips into the NEXT auction_item and grabs its lot number --
#        confirmed on a full file: 100% of bare-digit "Result" values
#        equal the following block's lot number. Harmless once known:
#        any Result that isn't "€ <amount>" means no sale, full stop.
#     2. `item.find("div", class_="lot_name")` (singular) only ever reads
#        the FIRST wine of a multi-wine lot (~31% of lots in the one 2012
#        month sampled against both formats) -- the rest of that lot is
#        silently dropped. Unrecoverable from this capture; mixed_lot
#        cannot be set here (stays 0/unknown), not because the lot wasn't
#        mixed, but because this source can no longer tell.
#   Separately: 3 file pairs across the full 2012-2026 archive are
#   byte-identical content saved under two different month names (a
#   capture mistake, not a real double auction) -- deduped by content
#   hash, not filename.

_SYLVIES_MONTHS = {
    "januar": 1, "january": 1, "februar": 2, "february": 2,
    "märz": 3, "marz": 3, "march": 3, "april": 4, "mai": 5, "may": 5,
    "juni": 6, "june": 6, "juli": 7, "july": 7, "august": 8,
    "september": 9, "oktober": 10, "october": 10, "november": 11,
    "dezember": 12, "december": 12,
}
_SYLVIES_MONTH_FILE = re.compile(r"^([A-Za-zäöüÄÖÜ]+)(\d{4,5})$")
# Three 2018 files have a typo'd 5-digit year ("August20218.txt" instead
# of "August2018.txt") -- the only copy of that month, not a duplicate of
# a correctly-named file, so skipping them would lose real data.
_SYLVIES_YEAR_TYPOS = {"20218": "2018"}


def _sylvies_month_key(basename):
    """'Februar2024.txt' / 'February2012.zip' -> ('2024', 2), or None."""
    m = _SYLVIES_MONTH_FILE.match(os.path.splitext(basename)[0])
    if not m:
        return None
    year = _SYLVIES_YEAR_TYPOS.get(m.group(2), m.group(2))
    if len(year) != 4:
        return None
    month = _SYLVIES_MONTHS.get(m.group(1).lower())
    return (year, month) if month else None


_SYLVIES_YEAR = re.compile(r"^(\d{4})\s+(.+)$")


def _sylvies_extract_vintage(name):
    name = (name or "").strip()
    m = _SYLVIES_YEAR.match(name)
    return (int(m.group(1)), m.group(2).strip()) if m else (None, name or None)


# Bottling/provenance shorthand, not a producer name -- "Mc" (mise en
# bouteille au château: bottled by the château itself, whose name is
# already the wine field for these lots), bare "Neg"/"Dom" (an unnamed
# négociant/domaine), "Dist" (distributeur). By far the single most
# common value in this field (89,664 of ~267k lots are bare "Mc") --
# storing it as producer would flood the producer index with a
# meaningless 2-letter bucket. "Neg. Jean Theil" etc. (a NAMED
# négociant) is unaffected -- only the bare code is excluded.
_SYLVIES_PROVENANCE_CODE = {"mc", "neg", "neg.", "dom", "dom.", "dist",
                           "dist."}


def _sylvies_split_description(desc):
    """'Italy | la Stoppa' -> (region, producer); order confirmed on the
    source HTML. Not always a true country/region (e.g. '1er Cru |
    Harmand Geoffroy' puts a classification tier there instead) --
    stored as-is, same raw-passthrough policy as every other loader."""
    desc = (desc or "").strip()
    if " | " not in desc:
        return desc or None, None
    region, producer = (p.strip() or None for p in desc.split(" | ", 1))
    if producer and producer.lower() in _SYLVIES_PROVENANCE_CODE:
        producer = None
    return region, producer


# "<N> x <size>[,.]<decimals> L[tr]" (explicit liters, e.g. "12 x 0,5 Ltr")
# takes priority over the named-format table when both could apply --
# consistent with the weinboerse loader's "explicit size wins" rule.
_SYLVIES_BOTTLE_LITER = re.compile(
    r"^(\d+)\s*x\s*(\d+(?:[.,]\d+)?)\s*l(?:tr)?\.?,?\s*(\S+)?",
    re.IGNORECASE)
_SYLVIES_BOTTLE_NAMED = re.compile(
    r"^(\d+)\s+(bott+le|magnum|magum|demi|dmagnum|imperial|"
    # "(s)" (not just a trailing "s"): the literal source text is
    # "Bottle(s)" -- without this alternative, "s?" only ever matches
    # zero characters (the next real char is "(", not "s"), and the
    # unconsumed ", Oc" marker falls through into the WRONG regex group.
    r"jeroboam|jéroboam|jroboam)(?:s|\(s\))?\.?,?\s*(\S+)?", re.IGNORECASE)
_SYLVIES_UNIT_DL = {
    "bottle": 7.5, "botttle": 7.5, "magnum": 15.0, "magum": 15.0,
    "demi": 3.75, "dmagnum": 30.0, "imperial": 60.0, "jeroboam": 50.0,
    "jéroboam": 50.0, "jroboam": 50.0,
}


def _sylvies_parse_bottle(text):
    """'<N> Bottle(s)[, Oc]' / '<N> x <size> Ltr[, Owc]' -> (quantity,
    bottle_size_dl, is_ohk). Markers beyond Oc/Owc (a handful of stray
    digits/words from drift in the source text) are left unflagged --
    an allowlist, not a blocklist, so an unrecognized marker can't cause
    a false OHK positive."""
    text = (text or "").strip()
    m = _SYLVIES_BOTTLE_LITER.match(text)
    if m:
        qty = int(m.group(1))
        dl = float(m.group(2).replace(",", ".")) * 10
        return qty, dl, _sylvies_is_ohk_marker(m.group(3))
    m = _SYLVIES_BOTTLE_NAMED.match(text)
    if m:
        qty = int(m.group(1))
        dl = _SYLVIES_UNIT_DL.get(m.group(2).lower())
        return qty, dl, _sylvies_is_ohk_marker(m.group(3))
    return None, None, False


def _sylvies_is_ohk_marker(marker):
    # "Owc-1"/"Oc-2" etc. (a numbered-case suffix) is by far the MORE
    # common form in this archive, not a rare variant -- 44,557 dash-
    # suffixed hits vs. the plain "Oc"/"Owc" count. Only the part before
    # the dash is the actual case-type marker.
    marker = (marker or "").strip(",.").lower().split("-")[0]
    return marker in ("oc", "owc")


_SYLVIES_ESTIMATE = re.compile(
    r"€\s*([\d.,]+)\s*-\s*€\s*([\d.,]+)")
_SYLVIES_PRICE = re.compile(r"^€\s*([\d.,]+)")


def _sylvies_parse_estimate(text):
    m = _SYLVIES_ESTIMATE.search(text or "")
    if not m:
        return None, None
    return to_float(m.group(1)), to_float(m.group(2))


def _sylvies_parse_result(text):
    """Anything other than a clean '€ <amount>' means no sale -- covers
    the literal "not been sold" text, the scraper's bare-next-lot-number
    bug (see module note above), and the rare untyped garbage alike;
    all three correctly resolve to "no price," not three different
    things to special-case."""
    m = _SYLVIES_PRICE.match((text or "").strip())
    if m:
        return to_float(m.group(1)), 1
    return None, 0


def load_sylvies_html(b, limit):
    """2012's 6 full-fidelity months: raw HTML, zipped, one page per
    'Resultatfile<N>.html'. Every lot_item in a multi-wine lot is read
    (unlike the txt capture, whose scraper only ever read the first)."""
    files = sorted(glob.glob(os.path.join(ARCHIVE, "sylvies", "*.zip")))
    n = 0
    for f in files:
        key = _sylvies_month_key(os.path.basename(f))
        if key is None:
            continue
        year, month = key
        b.set_source(f)
        a_id = b.add_auction("sylvies", f"sylvies_{year}-{month:02d}",
                             f"sylvies {year}-{month:02d}",
                             f"{year}-{month:02d}-01", "EUR", "HAMMER")
        with zipfile.ZipFile(f) as zf:
            for name in zf.namelist():
                if not name.endswith(".html"):
                    continue
                html = zf.read(name).decode("utf-8", errors="replace")
                soup = BeautifulSoup(html, "html.parser")
                for it in soup.find_all("div", class_="auction_item"):
                    row = _sylvies_parse_html_item(it)
                    if row:
                        b.add_lot(a_id, row)
        n += 1
        if limit and n >= limit:
            break


def _sylvies_parse_html_item(item):
    lot_nr_el = item.find("p", class_="lot_nr")
    lot_no = lot_nr_el.get_text(strip=True) if lot_nr_el else None
    if not lot_no:
        return None

    subs = []
    for li in item.find_all(
            "div", class_=lambda c: c and c.startswith("lot_item")):
        name_el = li.find("div", class_="lot_name")
        desc_el = li.find("div", class_="lot_description")
        bottle_el = li.find("div", class_="lot_bottle")
        bt_el = li.find("div", class_="lot_bottle_type")
        vintage, wine = _sylvies_extract_vintage(
            name_el.get_text(strip=True) if name_el else None)
        region, producer = _sylvies_split_description(
            desc_el.get_text(strip=True) if desc_el else None)
        qty, dl, is_ohk = _sylvies_parse_bottle(
            bottle_el.get_text(strip=True) if bottle_el else None)
        subs.append({
            "wine": wine, "vintage": vintage, "region": region,
            "producer": producer, "quantity": qty, "bottle_size_dl": dl,
            "is_ohk": is_ohk,
            "condition_text": (bt_el.get_text(strip=True) if bt_el else
                               None) or None,
        })
    if not subs:
        return None

    est_el = item.find("div", class_="lot_estimate")
    estimate_low = estimate_high = None
    if est_el:
        p = est_el.find_next_sibling("p")
        if p:
            estimate_low, estimate_high = _sylvies_parse_estimate(
                p.get_text(strip=True))
    bid_el = item.find("div", class_="lot_my_bid")
    result_text = None
    if bid_el and bid_el.parent:
        # The unsold case is a bare text node (no <p>) right after this
        # div, inside the SAME parent -- read the whole parent's text,
        # not find_next("p"), which would run past it into other lots.
        result_text = re.sub(r"^\s*Result\s*", "",
                              bid_el.parent.get_text(strip=True),
                              flags=re.IGNORECASE)
    hammer, sold = _sylvies_parse_result(result_text)

    if len(subs) == 1:
        s = subs[0]
        return {
            "lot_no": lot_no, "wine": s["wine"], "vintage": s["vintage"],
            "region": s["region"], "producer": s["producer"],
            "quantity": s["quantity"], "bottle_size_dl": s["bottle_size_dl"],
            "is_ohk": 1 if s["is_ohk"] else 0,
            "condition_text": s["condition_text"], "mixed_lot": None,
            "hammer_price": hammer, "sold": sold, "price_basis":
            "HAMMER" if sold else "UNKNOWN", "currency": "EUR",
            "estimate_low": estimate_low, "estimate_high": estimate_high,
        }

    producers = {s["producer"] for s in subs if s["producer"]}
    regions = {s["region"] for s in subs if s["region"]}
    quantities = [s["quantity"] for s in subs if s["quantity"]]
    return {
        "lot_no": lot_no,
        "wine": "; ".join(
            f"{s['vintage']} {s['wine']}" if s["vintage"] else s["wine"]
            for s in subs if s["wine"]),
        "vintage": None,
        "producer": producers.pop() if len(producers) == 1 else None,
        "region": regions.pop() if len(regions) == 1 else None,
        "quantity": sum(quantities) if quantities else None,
        "bottle_size_dl": None,
        "is_ohk": 1 if any(s["is_ohk"] for s in subs) else 0,
        "condition_text": "; ".join(
            s["condition_text"] for s in subs if s["condition_text"]
        ) or None,
        "mixed_lot": 1,
        "hammer_price": hammer, "sold": sold,
        "price_basis": "HAMMER" if sold else "UNKNOWN", "currency": "EUR",
        "estimate_low": estimate_low, "estimate_high": estimate_high,
    }


def _sylvies_html_covered_months(conn):
    """(year, month) keys already loaded by load_sylvies_html, so the txt
    capture of the same month (lower fidelity -- see module note) is
    skipped rather than double-loading it. Mirrors
    ``_wermuth_xlsx_dates``."""
    rows = conn.execute(
        "SELECT a.auction_id FROM auctions a JOIN providers p"
        " ON a.provider_id = p.id WHERE p.name = 'sylvies'").fetchall()
    covered = set()
    for (aid,) in rows:
        m = re.match(r"^sylvies_(\d{4})-(\d{2})$", aid or "")
        if m:
            covered.add((m.group(1), int(m.group(2))))
    return covered


def load_sylvies_txt(b, limit):
    """Every month 2012-2026 not already covered by load_sylvies_html --
    the STDOUT capture of running the (buggy) sylviesParser live. See the
    module note above for the two bugs baked into this source."""
    files = sorted(glob.glob(
        os.path.join(ARCHIVE, "sylvies", "**", "*.txt"), recursive=True))
    covered = _sylvies_html_covered_months(b.conn)
    seen_hashes = set()
    n = 0
    for f in files:
        with open(f, "rb") as fh:
            raw = fh.read()
        digest = hashlib.sha256(raw).hexdigest()
        # Hash BEFORE the key/covered check, not after: one of a
        # duplicate-content pair is always a zip-covered 2012 month
        # (skipped below), and if that check ran first, the skipped
        # file would never reach seen_hashes -- its byte-identical
        # twin under a different (wrong) month label would then load
        # as if it were a real, separate auction.
        if digest in seen_hashes:
            continue
        seen_hashes.add(digest)
        key = _sylvies_month_key(os.path.basename(f))
        if key is None:
            print(f"WARN load_sylvies_txt: unrecognized filename {f}")
            continue
        if key in covered:
            continue
        year, month = key
        b.set_source(f)
        a_id = b.add_auction("sylvies", f"sylvies_{year}-{month:02d}",
                             f"sylvies {year}-{month:02d}",
                             f"{year}-{month:02d}-01", "EUR", "HAMMER")
        text = raw.decode("utf-8", errors="replace")
        # Per-block dedup, not just a whole-file one: 2 files (2021/
        # October, 2021/December) are their own content twice over end
        # to end (a capture artifact -- the whole scrape run saved
        # twice into one file), and at least one lot elsewhere repeats
        # just once within an otherwise-unique file (a page re-fetched
        # on retry, printed twice). Same mechanism either way -- a
        # scrape/save step ran part of its output twice -- so one
        # dedup catches both instead of two separate special cases.
        seen_blocks = set()
        for block in text.split("-" * 40):
            stripped = block.strip()
            if not stripped or stripped in seen_blocks:
                continue
            seen_blocks.add(stripped)
            row = _sylvies_parse_txt_block(block)
            if row:
                b.add_lot(a_id, row)
        n += 1
        if limit and n >= limit:
            break


def _sylvies_txt_field(block, name):
    # [ \t]*, not \s*: \s matches newline too, so a blank field ("Lot
    # Bottletype: " followed immediately by a newline) would otherwise
    # let the match skip past it and capture the START OF THE NEXT LINE
    # instead of the empty value (confirmed: this leaked "Estimate: € ..."
    # text into condition_text on every lot with no condition notes).
    m = re.search(rf"{re.escape(name)}:[ \t]*(.*)", block)
    return m.group(1).strip() if m else None


def _sylvies_parse_txt_block(block):
    lot_no = _sylvies_txt_field(block, "Lot Number")
    if not lot_no:
        return None
    vintage, wine = _sylvies_extract_vintage(
        _sylvies_txt_field(block, "Lot Name"))
    region, producer = _sylvies_split_description(
        _sylvies_txt_field(block, "Lot Description"))
    qty, dl, is_ohk = _sylvies_parse_bottle(
        _sylvies_txt_field(block, "Lot Bottle"))
    estimate_low, estimate_high = _sylvies_parse_estimate(
        _sylvies_txt_field(block, "Estimate") or "")
    hammer, sold = _sylvies_parse_result(_sylvies_txt_field(block, "Result"))
    is_vat = bool(re.search(r"\bVAT LOT\b|\bBTW LOT\b", block, re.IGNORECASE))

    return {
        "lot_no": lot_no, "wine": wine, "vintage": vintage,
        "region": region, "producer": producer, "quantity": qty,
        "bottle_size_dl": dl, "is_ohk": 1 if is_ohk else 0,
        "condition_text": _sylvies_txt_field(block, "Lot Bottletype") or None,
        "mixed_lot": None, "hammer_price": hammer, "sold": sold,
        "price_basis": "HAMMER" if sold else "UNKNOWN", "currency": "EUR",
        "estimate_low": estimate_low, "estimate_high": estimate_high,
        "note": "VAT LOT" if is_vat else None,
    }


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
    # results_316.xlsx (531 lots, an early OCR pass of the 04.05.2002
    # auction) duplicates load_steinfels_staging's "Steinfels_04.05.2002"
    # event (832 lots, same lots -- e.g. lot 1 "Valandraud" 1998 CHF 1850 in
    # both). The staging extraction is the more complete one; skip the
    # standalone file so the auction isn't double-counted.
    files = [f for f in files if os.path.basename(f) != "results_316.xlsx"]
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
            # Most prepared/*.xlsx store the deciliter value directly under
            # "Unit"; 315/316 are the exception, with "Unit" holding the raw
            # label (e.g. "Flaschen") and "Unit_DL" the converted number.
            bottle_size_dl = (to_float(_v(rec, "Unit_DL"))
                               or to_float(_v(rec, "Unit")))
            b.add_lot(a_id, {
                "lot_no": str(_v(rec, "Lot")),
                "wine": _v(rec, "Wine"),
                "producer": _clean(_v(rec, "Producer")),
                "region": _clean(_v(rec, "Region")),
                "vintage": to_int(_v(rec, "Year")),
                "quantity": to_int(_v(rec, "Quantity")),
                "bottle_size_dl": bottle_size_dl,
                "hammer_price": to_float(_v(rec, "Price_CHF")),
                "price_basis": "HAMMER", "currency": "CHF",
            })
        n += 1
        if limit and n >= limit:
            break
    # The Alt-XLSX (2002-03) is numbered by sequential file number, not a
    # platform auction id; the API-JSON/historical-dump ids come from the
    # platform itself and run low enough to collide with it by pure
    # coincidence (see _load_weinauktion_json's aid_prefix docstring) --
    # both need the same prefix to stay in a namespace of their own.
    remaining = None if limit is None else max(0, limit - n)
    # `_load_weinauktion_json`/`_load_steinfels_resultfile_json`'s own
    # `if limit and n >= limit` treats 0 as falsy (unlimited), so a used-up
    # budget must skip the calls outright rather than pass 0 through (see
    # load_weinboerse).
    if remaining is None or remaining > 0:
        _load_weinauktion_json(b, "steinfels", remaining, aid_prefix="api-")
        _load_steinfels_resultfile_json(b, remaining)


def _load_steinfels_resultfile_json(b, limit):
    """Historical raw export of the weinauktion platform's own paginated
    API response (confirmed: 3,904 files, 2016-2026, e.g. "Auktion 408" --
    CHF 12% Kommission + CHF 10 Lotgebühr, matches docs/premium-policy.md).
    Same ``{"@related": {auctions, catalogs, parts}, "items": [...]}``
    shape ``load_weinboerse`` already handles for weinboerse's identical
    platform -- this is the steinfels-side fix for the same gap: steinfels
    looked "frozen since 2016" only because nothing ever read these files
    or the CI-fetched ones (see the x-api-version fix in
    ingest/fetchers/weinauktion.py), not because the house stopped
    running auctions (it is mid "eAuktion 125" as of 2026-11-01).

    Field mapping deliberately stays as flat as the live fetcher's own
    ``_map_lot`` (ingest/fetchers/weinauktion.py) -- wine text + a
    vintage regex, not weinboerse's richer producer/quantity/OHK
    free-text parse -- since steinfels' live-fetched lots never got that
    treatment either; consistency with the live path matters more than
    per-house parsing depth here.
    """
    files = _json_files("Steinfels", "**/Resultfile*.json")
    auctions, catalogs, parts = {}, {}, {}
    for f in files:
        rel = load_json(f).get("@related", {})
        for a in rel.get("auctions", []):
            auctions[a["id"]] = a
        for c in rel.get("catalogs", []):
            catalogs[c["id"]] = c
        for p in rel.get("parts", []):
            parts[p["id"]] = p
    part_to_auction = {
        pid: catalogs[p["auctionCatalogId"]]["auctionId"]
        for pid, p in parts.items() if p.get("auctionCatalogId") in catalogs
    }

    # Mirrors load_weinboerse: an auction the CI fetcher has already
    # written as its own "steinfels/<catalog_id>.json" ({auction, lots}
    # shape) wins over this frozen dump, so a future CI refetch of the
    # same catalog is not double-loaded on top of it.
    fetched_auction_ids = set()
    for f in _json_files("steinfels"):
        if os.path.basename(f).lower().startswith("resultfile"):
            continue
        cat_id = os.path.splitext(os.path.basename(f))[0]
        cat = catalogs.get(int(cat_id)) if cat_id.isdigit() else None
        if cat:
            fetched_auction_ids.add(cat["auctionId"])

    seen = set()
    auction_db_id = {}
    n = 0
    for f in files:
        d = load_json(f)
        b.set_source(f)
        for it in d.get("items", []):
            if limit and n >= limit:
                break
            key = (it.get("auctionCatalogPartId"), it.get("id"))
            if key in seen:
                continue
            seen.add(key)
            aid = part_to_auction.get(key[0])
            if aid in fetched_auction_ids:
                continue
            a = auctions.get(aid)
            if a is None:
                continue
            if aid not in auction_db_id:
                auction_db_id[aid] = b.add_auction(
                    "steinfels", f"api-{aid}", a.get("title"),
                    parse_date(a.get("startDate")),
                    a.get("currency") or "CHF", "HAMMER")
            a_id = auction_db_id[aid]

            text = _wb_strip_html(
                it.get("shortDescription") or it.get("description") or "")
            m = re.search(r"\b(19|20)\d{2}\b", text)
            sold = it.get("state") == "sold"
            # upperBasePrice==0.0 is a null sentinel, not a real CHF-0
            # estimate -- confirmed: it's exactly 0 for 26% of a random
            # sample, and on those same lots basePrice always equals
            # startingBid (no real estimate was ever entered, only a
            # starting bid), while recent auctions (e.g. "Auktion 408",
            # 2023) use both fields as a genuine low/high estimate range.
            # That evidence covers upperBasePrice only -- basePrice has no
            # equivalent sentinel pattern, so a genuine CHF-0 low estimate
            # is kept rather than squashed to None.
            estimate_low = to_float(it.get("basePrice"))
            estimate_high = to_float(it.get("upperBasePrice")) or None
            b.add_lot(a_id, {
                "lot_no": str(it.get("number")),
                "source_lot_key": f"{key[0]}:{key[1]}",
                "wine": text or None,
                "vintage": to_int(m.group(0)) if m else None,
                "estimate_low": estimate_low,
                "estimate_high": estimate_high,
                "hammer_price": to_float(it.get("hammerPrice")),
                "sold": 1 if sold else 0,
                "price_basis": "HAMMER" if sold else "UNKNOWN",
                "currency": a.get("currency") or "CHF",
            })
            n += 1
        if limit and n >= limit:
            break


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
        # The 04.05.2002 sheet has 57 lot numbers whose row is repeated
        # verbatim 11 or 12 times in the raw file itself (confirmed: one
        # worksheet, read once -- not a loader bug, a transcription
        # artifact in this staging workbook). Keep only the first
        # occurrence per (lot_no, wine, vintage, quantity, region, price).
        seen = set()
        deduped = []
        for rec in lots:
            key = (str(_v(rec, "providerOfferingId")), _v(rec, "name"),
                   to_int(_v(rec, "vintage")), to_int(_v(rec, "noOfBottles")),
                   _clean(_v(rec, "region")),
                   to_float(_v(rec, "realizedPrice")))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(rec)
        for rec in deduped:
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


# --- Denz archive (Wermuth PDF/HTML catalogs+results, 2003-2026) ----------- #
#
# Despite the folder name "Denz", every file here is a Wermuth auction
# document -- "Wermuth_WZ-156.pdf", internal footer path ".../Wein/
# Wermuth/2003/WZ_156.html" -- loaded into the SAME "wermuth-sa" provider
# as load_wermuth/load_wermuth_validated above, not a new house.
#
# Two eras, forced by what actually survives in the archive:
# - ~2003-2011: a pre-sale catalog PDF (wine name/region as a STICKY
#   header shared by however many numbered lot lines follow, estimate
#   only) plus a SEPARATE results HTML table (lot number + price only,
#   no wine text at all) -- joined by lot/catalog number.
# - ~2012-2026: a single self-contained "*Resultate*.pdf": wine
#   description, estimate AND the realized price ("Zuschlag") in one row,
#   no join needed.
#
# Decades of ad-hoc filenames (two dozen+ distinct conventions observed,
# e.g. "280_Nachverkaufsliste.pdf", "WZ-255_14112015_Resultate_
# ManuallyImproved.pdf", "Resultate_Denz_Auktion_263.pdf") make a strict
# glob unreliable; files are classified by what their name CONTAINS
# ("resultat"/"ergebnisliste"/"nachverkauf", case-insensitive) rather
# than a fixed pattern. "Nachverkaufsliste" (after-sale list) is loaded
# alongside the main "Resultate" file for the same catalog, not instead
# of it -- it covers lots that didn't sell at the auction itself.
#
# Dates 2008-02-28 through 2018-03-13 (51 auctions) are already covered
# by the xlsx/CSV Wermuth sources above -- skipped by auction date, the
# same dedup pattern load_wermuth_validated uses against load_wermuth.

_WERMUTH_UNIT_DL = {
    "flasche": 7.5, "flaschen": 7.5,
    "magnumflasche": 15.0, "magnumflaschen": 15.0, "magnum": 15.0,
    "doppelmagnum": 30.0, "doppelmagnumflasche": 30.0,
    "jeroboam": 50.0, "jeroboamflasche": 50.0,
}
_WERMUTH_UNIT_PAT = (r"Dutzend\s+Flaschen|Flaschen?|Magnumflaschen?|Magnum|"
                     r"Doppelmagnum(?:flaschen?)?|Jeroboam(?:flaschen?)?")
_WERMUTH_RESULT_RE = re.compile(r"(?:SFr\.?|CHF)\s*([\d'’.,]+)\s*$",
                                re.IGNORECASE)
_WERMUTH_ESTIMATE_RE = re.compile(
    r"(?:Sfr\.?|CHF)\s*([\d'’.,]+)\s*-\s*([\d'’.,]+)\s*$", re.IGNORECASE)
_WERMUTH_PRO_UNIT_RE = re.compile(r"\bpro\s+\S+\s*$", re.IGNORECASE)
_WERMUTH_OHK_RE = re.compile(
    r",?\s*(?:in\s+)?(?:\d+er\s+)?\b(OHK|OC|MS)\b\.?\s*$", re.IGNORECASE)
_WERMUTH_VINTAGE_RE = re.compile(r",?\s*(\d{4})\s*$")
_WERMUTH_QTY_UNIT_RE = re.compile(
    # The bottle-size fraction (half-/eighth-bottles) appears both
    # space- and hyphen-joined to the unit word across this archive --
    # "12 3/8 Flaschen" and "12 3/8-Flaschen" are both real. Missing
    # either joiner here used to make the whole fraction fall through
    # unmatched, so the regex instead matched a bare "8 Flaschen" at the
    # tail (misreading the fraction's denominator as the quantity) and
    # left "12 3/" stuck in the wine/producer text.
    r"(\d+)\s*(?:(\d+)/(\d+)[\s-])?(" + _WERMUTH_UNIT_PAT + r")\s*,?\s*$",
    re.IGNORECASE)


def _wermuth_money(tok):
    return to_float(tok.replace("’", "").replace("'", ""))


def _wermuth_parse_tail(text):
    """Strip, right to left, whatever of '<wine desc> <qty> <unit>,
    <vintage>[, OHK] pro <X> Sfr. <low>-<high> SFr. <result>' is present.
    A catalog line has no result; an early-era line has no wine desc
    (it's a sticky header elsewhere) -- same parser handles both, each
    simply leaving its missing piece as None/empty."""
    m = _WERMUTH_RESULT_RE.search(text)
    hammer = None
    if m:
        hammer = _wermuth_money(m.group(1))
        text = text[:m.start()].strip()
    m = _WERMUTH_ESTIMATE_RE.search(text)
    est_low = est_high = None
    if m:
        est_low, est_high = _wermuth_money(m.group(1)), _wermuth_money(m.group(2))
        text = text[:m.start()].strip()
        if est_low is not None and est_high is not None and est_high < est_low:
            # A narrow PDF column truncates the high estimate's last
            # digit in the original source (confirmed: "Sfr. 2100-300"
            # is the literal text, not a parse error) -- not
            # recoverable, and a backwards range is worse than none.
            est_low = est_high = None
    m = _WERMUTH_PRO_UNIT_RE.search(text)
    if m:
        text = text[:m.start()].strip()
    is_ohk = False
    m = _WERMUTH_OHK_RE.search(text)
    if m:
        is_ohk = m.group(1).upper() in ("OHK", "OC")
        text = text[:m.start()].strip()
    vintage = None
    m = _WERMUTH_VINTAGE_RE.search(text)
    if m:
        vintage = int(m.group(1))
        text = text[:m.start()].strip()
    quantity = bottle_size_dl = None
    m = _WERMUTH_QTY_UNIT_RE.search(text)
    if m:
        quantity = int(m.group(1))
        if m.group(2):
            bottle_size_dl = (int(m.group(2)) / int(m.group(3))) * 10
        else:
            unit = m.group(4).lower()
            if "dutzend" in unit:
                quantity *= 12
                bottle_size_dl = 7.5
            else:
                bottle_size_dl = _WERMUTH_UNIT_DL.get(unit)
        text = text[:m.start()].strip()
    return (text.strip(), quantity, bottle_size_dl, vintage, is_ohk,
            est_low, est_high, hammer)


_WERMUTH_ESTATE_PREFIX = re.compile(
    r"^(Château|Chateau|Clos|Domaine|Weingut)\b", re.IGNORECASE)
# A Bordeaux classification rank ("5e grand cru classé", "cru bourgeois",
# "grand cru exceptionnel", a bare "3e grand" where the rest wrapped onto
# the PDF's next line and was lost) -- never a producer, even though it
# sits in the same trailing comma slot a real producer name would.
_WERMUTH_CLASSIFICATION_WORD = re.compile(
    r"grand\s+cru|cru\s+class|cru\s+bourgeois|cru\s+exceptionnel|^\d+e?r?\b",
    re.IGNORECASE)
_WERMUTH_TRAILING_TOTAL = re.compile(r"\s+Total$")
_WERMUTH_MIXLOT_PREFIX = re.compile(r"^Mix[-\s]?[Ll]ot\b", re.IGNORECASE)
# Usually "<wine>, <code>, <region>..." (comma before the code) -- but on
# some files the comma before the code is simply missing ("Château Rol
# Valentin                      AC/ MC, St. Em ilion, grand cru"),
# gluing the appellation code onto the end of the wine name itself.
_WERMUTH_EMBEDDED_CODE_RE = re.compile(
    r"\s+((?:AC|AOC|MO|DOCG?|VdT|IGT|DO)(?:\s*/\s*[A-Z]{1,6})?)\s*$")


def _wermuth_split_wine_desc(desc):
    """'Dom Pérignon, AC/MO, Champagne, Moët & Chandon' -> (wine, producer,
    region, classification); order confirmed on the source. A bare
    château name (no commas at all) has no separate producer given --
    the château itself is implicitly the producer."""
    desc = _WERMUTH_TRAILING_TOTAL.sub("", desc).strip()
    parts = [p.strip() for p in desc.split(",") if p.strip()]
    if parts:
        m = _WERMUTH_EMBEDDED_CODE_RE.search(parts[0])
        if m and len(parts[0][:m.start()].strip()) >= 3:
            code = re.sub(r"\s*/\s*", "/", m.group(1))
            parts[0] = parts[0][:m.start()].strip()
            parts.insert(1, code)
    wine = parts[0] if parts else None
    producer = parts[-1] if len(parts) >= 3 else None
    region = parts[-2] if len(parts) >= 3 else None
    classification = ", ".join(parts[1:-2]) if len(parts) >= 4 else None
    if producer and _WERMUTH_CLASSIFICATION_WORD.search(producer):
        classification = (f"{classification}, {producer}" if classification
                          else producer)
        producer = None
    if producer is None and wine and _WERMUTH_ESTATE_PREFIX.match(wine):
        producer = wine
    return wine, producer, region, classification


_WERMUTH_SKIP_LINE = re.compile(
    # "Seite"/"file:///"/"^WZ[-\s]"/"^\x0c": repeating page header/footer.
    # ".html": the SAME page-footer's very first occurrence has no
    # leading form-feed to anchor on (it's the top of the file, not a
    # page break) and no "file:///" prefix either on some PDFs -- just
    # the bare "<date>  <file>.html" -- so catch it by what never
    # otherwise appears in a wine line instead.
    # "<t[dr]>": one PDF's text layer is literally unrendered HTML
    # markup for a few lines (print-to-PDF artifact), not real text.
    r"^\s*$|Seite|file:///|^WZ[-\s]|^\x0c|\.html\b|</?t[dr]>")
_WERMUTH_HEADER2_RE = re.compile(
    r"^[A-Z]{1,6}(?:\s*/\s*[A-Z]{1,6})?,\s*(.+)$")


def _wermuth_parse_catalog_pdf(text):
    """Pre-sale catalog: a wine-name line, an optional '<code>, <region>
    [, <classification>][, <producer>]' line, then one or more numbered
    lot lines that inherit that sticky header until the next wine name."""
    wine = producer = region = classification = None
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or _WERMUTH_SKIP_LINE.search(line):
            continue
        lot_m = re.match(r"^(\d+)\s+(.+)$", line)
        if lot_m:
            rest, qty, dl, vintage, is_ohk, est_low, est_high, _ = (
                _wermuth_parse_tail(lot_m.group(2)))
            if qty is None:
                continue  # not actually a lot line (e.g. a page number)
            yield {
                "lot_no": lot_m.group(1), "wine": wine, "producer": producer,
                "region": region, "classification": classification,
                "quantity": qty, "bottle_size_dl": dl, "vintage": vintage,
                "is_ohk": is_ohk, "estimate_low": est_low,
                "estimate_high": est_high,
                "mixed_lot": (1 if wine and _WERMUTH_MIXLOT_PREFIX.match(wine)
                              else None),
            }
            continue
        h2 = _WERMUTH_HEADER2_RE.match(line)
        if h2:
            parts = [p.strip() for p in line.split(",") if p.strip()]
            region = parts[1] if len(parts) >= 2 else None
            producer = parts[-1] if len(parts) >= 3 else None
            classification = (", ".join(parts[2:-1])
                              if len(parts) >= 4 else None)
            if producer and _WERMUTH_CLASSIFICATION_WORD.search(producer):
                classification = (f"{classification}, {producer}"
                                  if classification else producer)
                producer = None
            if producer is None and wine and _WERMUTH_ESTATE_PREFIX.match(wine):
                producer = wine
            continue
        wine = _WERMUTH_TRAILING_TOTAL.sub("", line).strip()
        producer = region = classification = None
        if _WERMUTH_ESTATE_PREFIX.match(wine):
            producer = wine


def _wermuth_parse_result_pdf(text):
    """Self-contained ~2012+ result PDF: one fully-formed lot per line."""
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or _WERMUTH_SKIP_LINE.search(line):
            continue
        lot_m = re.match(r"^(\d+)\s+(.+)$", line)
        if not lot_m:
            continue
        desc, qty, dl, vintage, is_ohk, est_low, est_high, hammer = (
            _wermuth_parse_tail(lot_m.group(2)))
        if qty is None or hammer is None or not desc:
            continue
        wine, producer, region, classification = _wermuth_split_wine_desc(desc)
        yield {
            "lot_no": lot_m.group(1), "wine": wine, "producer": producer,
            "region": region, "classification": classification,
            "quantity": qty, "bottle_size_dl": dl, "vintage": vintage,
            "is_ohk": is_ohk, "estimate_low": est_low,
            "estimate_high": est_high, "hammer_price": hammer,
            "mixed_lot": (1 if wine and _WERMUTH_MIXLOT_PREFIX.match(wine)
                          else None),
        }


def _wermuth_parse_results_html(html_text):
    """Early-era results table: Lot | Preis | Menge | Total -> {lot_no:
    hammer_price}, keyed off the lot-level Total (not the per-unit
    Preis)."""
    soup = BeautifulSoup(html_text, "html.parser")
    out = {}
    for tr in soup.find_all("tr")[1:]:
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) < 4:
            continue
        total = to_float(cells[3])
        if total:
            out[cells[0]] = total
    return out


_GERMAN_MONTHS = {
    "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
    "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11,
    "dezember": 12,
}
_WERMUTH_DATE_TEXT_RE = re.compile(
    r"\b(\d{1,2})\.\s*(Januar|Februar|März|April|Mai|Juni|Juli|August|"
    r"September|Oktober|November|Dezember)\s+(\d{4})\b", re.IGNORECASE)


def _wermuth_date_from_text(text):
    m = _WERMUTH_DATE_TEXT_RE.search(text)
    if not m:
        return None
    month = _GERMAN_MONTHS[m.group(2).lower()]
    return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"


def _wermuth_date_from_filename(path):
    m = re.search(r"(\d{2})(\d{2})(\d{4})", os.path.basename(path))
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else None


def _wermuth_catalog_number(path):
    name = os.path.basename(path)
    m = re.search(r"WZ[-_\s]?(\d+)", name, re.IGNORECASE)
    if m:
        return m.group(1)
    m = re.search(r"Auktion[-_\s]?(\d{2,3})(?=[-_\s.]|$)", name, re.IGNORECASE)
    if m:
        return m.group(1)
    # Not \b: "265_Resultate Web.pdf" has a digit run directly followed
    # by "_", and \w (which \b straddles) includes the underscore, so a
    # word-boundary assertion never holds there -- every bare-leading-
    # number filename ("261-Resultate.pdf", "280_Nachverkaufsliste.pdf")
    # silently failed to match and fell back to using the whole filename
    # as the catalog number instead, splitting one real auction across
    # two different auction_ids (one per filename convention).
    m = re.match(r"^(\d{2,3})(?=[-_\s.]|$)", name)
    return m.group(1) if m else None


def _wermuth_pdf_text(pdf_path):
    # -enc UTF-8 is not pdftotext's default -- without it, a PDF whose
    # internal font encoding isn't already UTF-8 comes out mis-decoded
    # (confirmed: "Côte" -> "CÃ´te" on some files, correct on others,
    # depending on that PDF's own font metadata).
    out = subprocess.run(
        ["pdftotext", "-layout", "-enc", "UTF-8", pdf_path, "-"],
        capture_output=True, encoding="utf-8", check=True)
    return out.stdout


def load_denz_wermuth(b, limit):
    covered_dates = _wermuth_xlsx_dates(b.conn)  # all wermuth-sa dates so far
    base = os.path.join(ARCHIVE, "Denz")
    seen_hashes = set()
    processed_wz = set()
    n = 0
    for year_dir in sorted(glob.glob(os.path.join(base, "*"))):
        if not os.path.isdir(year_dir):
            continue
        files = sorted(glob.glob(os.path.join(year_dir, "**", "*.pdf"),
                                 recursive=True))
        htmls = sorted(glob.glob(os.path.join(year_dir, "**", "*.html"),
                                 recursive=True))
        result_pdfs = [f for f in files if re.search(
            r"resultat|ergebnisliste|nachverkauf", os.path.basename(f),
            re.IGNORECASE)]
        catalog_pdfs = [f for f in files if f not in result_pdfs]
        result_htmls = [f for f in htmls if re.search(
            r"resultat", os.path.basename(f), re.IGNORECASE)]
        # A self-contained result PDF (2012+) never prints the auction
        # date anywhere in its own text -- confirmed empirically, not
        # just a parse miss. Resolve the date from WHATEVER file shares
        # its catalog number, not just the one file that happens to
        # supply the lots: filename-date-bearing files ("WZ-264_
        # 13032018_Resultate.pdf") and bare ones ("264-Resultate.pdf",
        # no date anywhere) both exist for the same real auction, and
        # alphabetical sort can put either one first.
        files_by_wz = {}
        for f in files:
            fwz = _wermuth_catalog_number(f)
            if fwz:
                files_by_wz.setdefault(fwz, []).append(f)

        def _resolve_date(wz):
            for cand in files_by_wz.get(wz, []):
                d = _wermuth_date_from_filename(cand)
                if d:
                    return d
            for cand in files_by_wz.get(wz, []):
                d = _wermuth_date_from_text(_wermuth_pdf_text(cand))
                if d:
                    return d
            return None

        # ~2012+: self-contained result PDFs.
        for f in result_pdfs:
            with open(f, "rb") as fh:
                raw = fh.read()
            digest = hashlib.sha256(raw).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            wz = _wermuth_catalog_number(f) or os.path.basename(f)
            if wz in processed_wz:
                # Decades of ad-hoc re-exports mean the SAME auction
                # often exists under 2-3 differently-named files (e.g.
                # "WZ-265_05052018_Resultate.pdf" and the separately
                # re-published "265_Resultate Web.pdf") -- not caught by
                # the exact-bytes hash dedup above since the files
                # genuinely aren't byte-identical. First file for a
                # given catalog number wins; later ones are skipped
                # outright rather than loaded under the same auction_id
                # a second time (which would just double every lot).
                continue
            text = _wermuth_pdf_text(f)
            lots = list(_wermuth_parse_result_pdf(text))
            if not lots:
                continue
            date = _resolve_date(wz)
            if date and date in covered_dates:
                continue
            processed_wz.add(wz)
            b.set_source(f)
            a_id = b.add_auction("wermuth-sa", f"denz-{wz}", f"WZ-{wz}",
                                 date, "CHF", "HAMMER")
            seen_lots = set()
            for lot in lots:
                if lot["lot_no"] in seen_lots:
                    continue
                seen_lots.add(lot["lot_no"])
                b.add_lot(a_id, {**lot, "price_basis": "HAMMER",
                                 "currency": "CHF", "sold": 1})
            n += 1
            if limit and n >= limit:
                return

        # ~2003-2011: catalog PDF + separate results HTML, joined by the
        # shared catalog (WZ) number. A catalog with no matching results
        # file is skipped -- no price data survives for it.
        for cat in catalog_pdfs:
            wz = _wermuth_catalog_number(cat)
            if wz is None or wz in processed_wz:
                continue
            html_match = next(
                (h for h in result_htmls
                 if _wermuth_catalog_number(h) == wz), None)
            if html_match is None:
                continue
            with open(cat, "rb") as fh:
                cat_raw = fh.read()
            digest = hashlib.sha256(cat_raw).hexdigest()
            if digest in seen_hashes:
                continue
            seen_hashes.add(digest)
            cat_text = _wermuth_pdf_text(cat)
            lots = list(_wermuth_parse_catalog_pdf(cat_text))
            if not lots:
                continue
            date = _resolve_date(wz)
            if date and date in covered_dates:
                continue
            processed_wz.add(wz)
            with open(html_match, encoding="utf-8", errors="replace") as fh:
                prices = _wermuth_parse_results_html(fh.read())
            a_id = b.add_auction("wermuth-sa", f"denz-{wz}", f"WZ-{wz}",
                                 date, "CHF", "HAMMER")
            b.set_source(cat)
            seen_lots = set()
            for lot in lots:
                if lot["lot_no"] in seen_lots:
                    continue
                seen_lots.add(lot["lot_no"])
                hammer = prices.get(lot["lot_no"])
                b.add_lot(a_id, {
                    **lot, "hammer_price": hammer,
                    "price_basis": "HAMMER" if hammer else "UNKNOWN",
                    "currency": "CHF", "sold": 1 if hammer else 0,
                })
            n += 1
            if limit and n >= limit:
                return


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
    ("denz-wermuth", load_denz_wermuth),
    ("steinfels", load_steinfels),
    ("steinfels-staging", load_steinfels_staging),
    ("weinboerse", load_weinboerse),
    ("sylvies-html", load_sylvies_html),
    ("sylvies-txt", load_sylvies_txt),
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

    _load_fx_rates(conn)
    _annotate_fx(conn)
    _apply_premium_policy(conn)
    _apply_tax(conn)
    _fill_lot_date(conn)
    _apply_fx_rates(conn)

    if not args.skip_resolution:
        from build_wines import run as resolve_wines
        resolve_wines(conn)

    _record_build_metadata(conn)


from fetch_fx import FX_CACHE  # noqa: E402  (single default for cache dir)


def _load_fx_rates(conn, cache_dir=None):
    """Load cached EODHD rates (``fetch_fx.py``) into ``fx_rates``; offline.

    Every ``EUR<CCY>.json`` is validated (ISO date, finite positive rate,
    ticker matches filename); a malformed file aborts the build rather than
    silently producing wrong conversions. A missing cache only warns -- the
    table stays empty and rows get no market ``fx_rate`` downstream.
    Returns the number of rows loaded.
    """
    cache_dir = cache_dir or FX_CACHE
    files = sorted(glob.glob(os.path.join(cache_dir, "EUR*.json")))
    if not files:
        print(f"WARN: no FX cache in {cache_dir} (run data/fetch_fx.py)")
        return 0
    conn.execute("DELETE FROM fx_rates")  # the cache is the source of truth
    loaded = 0
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                doc = json.load(fh)
            ccy = doc["currency"]
            if os.path.basename(path) != f"EUR{ccy}.json":
                raise ValueError(f"currency {ccy!r} does not match filename")
            if not doc["rows"]:
                raise ValueError("no rows")
            rows, seen = [], set()
            for d, rate in doc["rows"]:
                if datetime.date.fromisoformat(d).isoformat() != d:
                    raise ValueError(f"non-canonical date {d!r}")
                if d in seen:
                    raise ValueError(f"duplicate date {d}")
                seen.add(d)
                if (isinstance(rate, bool)
                        or not isinstance(rate, (int, float))
                        or not 0 < rate < 1e6):
                    raise ValueError(f"bad rate {rate!r} on {d}")
                rows.append((ccy, d, float(rate), doc.get("source", "EODHD")))
        except (OSError, ValueError, KeyError, TypeError) as e:
            raise ValueError(f"{path}: {type(e).__name__}: {e}") from e
        conn.executemany(
            "INSERT INTO fx_rates(currency, date, per_eur, source)"
            " VALUES (?, ?, ?, ?)", rows)
        loaded += len(rows)
    return loaded


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


def _apply_fx_rates(conn):
    """Annotate market currencies (AUD/USD/GBP/CHF/HKD/SGD/CNY) with their
    historical EUR rate on ``lot_date`` (Issue #97).

    ``fx_rates`` (loaded by ``_load_fx_rates`` from the EODHD cache) has one
    row per currency per *trading* day -- weekends/holidays have no row.
    For each lot, uses the nearest available rate on or before ``lot_date``
    (the standard FX convention: never a future rate) and records which
    date that rate actually came from in ``fx_rate_date``, since it can
    differ from ``lot_date`` itself. A lot dated before that currency's
    earliest cached rate (e.g. EURAUD only starts 2006-03-01, but langtons
    has AUD lots from the 1990s) gets no rate -- extrapolating backwards
    would be a guess, not a lookup. Only currencies already in _FX_FIX
    (fixed legal rates, not market-quoted) are excluded; NLG is not in
    ``fx_rates`` at all, so the WHERE clause already leaves it alone.
    Must run after ``_fill_lot_date`` so the auction-date fallback is
    already applied.
    """
    by_currency = {}
    for currency, date, per_eur in conn.execute(
            "SELECT currency, date, per_eur FROM fx_rates ORDER BY currency, date"):
        by_currency.setdefault(currency, ([], []))
        dates, rates = by_currency[currency]
        dates.append(date)
        rates.append(per_eur)

    for currency, (dates, rates) in by_currency.items():
        updates = []
        for lot_id, lot_date in conn.execute(
                "SELECT id, lot_date FROM lots WHERE currency = ?"
                " AND lot_date IS NOT NULL AND fx_rate IS NULL", (currency,)):
            i = bisect.bisect_right(dates, lot_date) - 1
            if i >= 0:
                updates.append((rates[i], dates[i], lot_id))
        conn.executemany(
            "UPDATE lots SET fx_rate = ?, fx_target_currency = 'EUR',"
            " fx_rate_date = ? WHERE id = ?", updates)


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
    "sylvies": {"rate": 0.20},
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
    31.02.2020) are left untouched and counted. One scan of ``lots`` (no index
    on lot_date). Returns ``(converted, invalid)``.
    """
    mapping = {}
    for (raw,) in conn.execute(
            "SELECT DISTINCT lot_date FROM lots WHERE lot_date LIKE '__.__.____'"
    ).fetchall():
        m = _DMY_DATE.match(raw)
        try:
            mapping[raw] = datetime.date(int(m.group(3)), int(m.group(2)),
                                         int(m.group(1))).isoformat()
        except (AttributeError, ValueError):
            pass
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS dmy_map("
                 "raw TEXT PRIMARY KEY, iso TEXT NOT NULL)")
    conn.execute("DELETE FROM dmy_map")
    conn.executemany("INSERT INTO dmy_map VALUES (?, ?)", mapping.items())
    converted = conn.execute(
        "UPDATE lots SET lot_date = (SELECT iso FROM dmy_map WHERE raw = lot_date)"
        " WHERE lot_date IN (SELECT raw FROM dmy_map)").rowcount
    conn.execute("DROP TABLE dmy_map")
    invalid = conn.execute(
        "SELECT COUNT(*) FROM lots WHERE lot_date LIKE '__.__.____'"
    ).fetchone()[0]
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
# langtons, christies, sylvies -- VAT is destination-dependent) are
# intentionally absent.
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
    load_dups, source_dups = _check_duplicate_lot_numbers(conn)
    if load_dups:
        # Not a hard gate YET: several houses besides christies (now
        # fixed) still carry this same bug, or an unresolved residual
        # (see _check_duplicate_lot_numbers's docstring) -- raising here
        # would break every build until all of them are cleaned up too,
        # which is separate, not-yet-scheduled work. Promote this to
        # `problems.append(...)` once that cleanup lands.
        print(f"WARN: duplicate-lot-number LOAD bug (same auction_id, "
              f"lot_no, wine, vintage, quantity, region, condition_text "
              f"AND is_ohk more than once): {load_dups} case(s) -- not "
              f"gated yet, see _validate_gates")
    if source_dups:
        print(f"WARN: {source_dups} case(s) of the same lot_no shared by "
              f"genuinely different rows within one auction -- either a "
              f"source data error (confirmed example: load_wermuth lot "
              f"299 on 19.10.2013, 'Contador' vs 'Giusto di Notri') or, "
              f"for langtons, that house's convention of grouping several "
              f"distinct sub-lots under one lot number. Not gated; needs "
              f"a per-house review, not a build failure.")
    if problems:
        raise RuntimeError("validation gates failed: " + "; ".join(problems))


def _check_duplicate_lot_numbers(conn):
    """(load_dups, source_dups): same (auction_id, lot_no) seen more than
    once, split by whether the repeated rows are byte-for-byte the same
    lot (a loader double-loading it -- the bug this session hit 6 times,
    in weinboerse/weinauktionator/sylvies/steinfels/denz-wermuth/christies,
    always from a second source or a second file naming the same real
    auction) or genuinely different rows sharing a reused lot_no (either
    a data error already in the xlsx/CSV Wermuth sources -- see
    docs/premium-policy.md's sibling note -- or, for langtons, that
    house's own cataloging convention of grouping several distinct
    sub-lots under one lot number).

    Content includes vintage, quantity, region and condition_text, not
    just wine+price -- each addition justified by a confirmed real
    langtons case where that field alone told two rows apart:
    - vintage: sale 1737 lot "1" -- three different vintages (1993/94/95)
      of the same wine share one lot number and winning bid.
    - quantity: sale 1746 lot "1197" -- 10 bottles vs. 2 "Stained Labels"
      bottles, same wine/vintage/price.
    - region: sale 1766 lot "2895" -- a mixed DRC lot with six different
      appellations (Echezeaux, La Tache, Richebourg, ...) sharing one lot
      number, vintage and price.
    - condition_text: sale 1763 lot "838" -- four ROCKFORD Black Sparkling
      Shiraz sub-lots, same wine/vintage/quantity/price, told apart only
      by disgorgement date in the notes.
    - is_ohk: wermuth-sa 13.03.2018 lot "331" -- "Trebbian d'Abruzzo"
      2009, same quantity/estimate/price, told apart only by whether the
      case is in its original wooden box (``is_ohk``).
    A small residual still lands in load_dups for langtons (e.g. sale
    1810 lot "2030"): rows that are byte-identical in every one of these
    fields too. Those are genuine raw-archive row repeats (no further
    field distinguishes them) rather than a loader bug -- the loader
    reads each sale from exactly one file, one row per raw lot entry.

    Uses COALESCE(vintage_final, vintage), not the raw loader column
    alone: several houses (winefields, zacky, munich-wine-company) embed
    the vintage in the free-text title instead of a separate field, so
    ``vintage`` is NULL at load time -- it's ``build_wines.py``'s
    ``_separate_vintage`` that extracts it into ``vintage_final`` and
    strips it out of ``wine``. Confirmed real case: winefields auction
    244 lot "170" has 7 raw rows for "Kopke Vintage Port"/"Kopke Colheita
    Port" that collapse onto one content tuple under the raw ``vintage``
    column (always NULL) -- comparing ``vintage_final`` instead resolves
    them into the correct 1960/1997/1997/1997/1999/1999 groups, the same
    class of false positive vintage already fixed for langtons. This
    check runs (via ``_validate_gates``, in ``main()``) after
    ``resolve_wines`` has populated ``vintage_final``, so the column is
    available; call sites that run it earlier see NULL and fall back to
    the raw ``vintage`` column, same as before."""
    rows = conn.execute(
        "SELECT auction_id, lot_no, wine, COALESCE(vintage_final, vintage),"
        " quantity, region, condition_text, is_ohk, hammer_price"
        " FROM lots WHERE lot_no IS NOT NULL").fetchall()
    seen = {}
    load_dups = source_dups = 0
    for auction_id, lot_no, wine, vintage, quantity, region, cond, ohk, \
            hammer in rows:
        key = (auction_id, lot_no)
        content = (wine, vintage, quantity, region, cond, ohk, hammer)
        if key not in seen:
            seen[key] = {content}
        elif content in seen[key]:
            load_dups += 1
        else:
            seen[key].add(content)
            source_dups += 1
    return load_dups, source_dups


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
