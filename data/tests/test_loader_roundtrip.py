"""Loader roundtrip: a normalized fetcher output must survive its loader.

Feeds the canonical ``{auction, lots}`` shape that each fetcher emits into its
matching ``load_*`` function and asserts the loader actually reads the fields
(no silent NULLs). This guards the fetcher<->loader field-name contract.
"""
import json
import os
import sqlite3
import tempfile
import unittest

import build_db
import build_wines


def _run_loader(house_dir, filename, data, loader_name):
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, house_dir), exist_ok=True)
        with open(os.path.join(d, house_dir, filename), "w",
                  encoding="utf-8") as fh:
            json.dump(data, fh)
        conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        old = build_db.ARCHIVE
        build_db.ARCHIVE = d
        try:
            getattr(build_db, loader_name)(builder, None)
        finally:
            build_db.ARCHIVE = old
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
        hammer = conn.execute(
            "SELECT COUNT(*) FROM lots WHERE hammer_price IS NOT NULL"
        ).fetchone()[0]
        wine = conn.execute(
            "SELECT COUNT(*) FROM lots WHERE wine IS NOT NULL"
        ).fetchone()[0]
        conn.close()
        return count, hammer, wine


class TestLoaderRoundtrip(unittest.TestCase):
    def test_apply_premium_policy(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "hammer_price": 100.0, "price_basis": "HAMMER",
                               "currency": "EUR"})
        build_db._apply_premium_policy(conn)
        row = conn.execute(
            "SELECT buyer_premium, fees, total_price, price_source FROM lots"
        ).fetchone()
        self.assertEqual(row, (10.0, 5.0, 115.0, "DERIVED"))
        conn.close()

    def test_apply_tax(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "hammer_price": 100.0, "price_basis": "HAMMER",
                               "currency": "EUR"})
        build_db._apply_premium_policy(conn)
        build_db._apply_tax(conn)
        row = conn.execute(
            "SELECT buyer_premium, fees, tax_amount, total_price, price_source"
            " FROM lots").fetchone()
        self.assertEqual(row, (10.0, 5.0, 1.9, 116.9, "DERIVED"))
        conn.close()

    def test_apply_fx_rates_uses_nearest_prior_trading_day(self):
        """fx_rates only has one row per *trading* day; a lot dated on a
        weekend/holiday must fall back to the nearest earlier rate, never
        a future one, and record which date that rate actually came from
        (fx_rate_date) since it can differ from the lot's own date."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("langtons", "1", "Langtons 1", None,
                                   "AUD", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x", "currency": "AUD",
                               "lot_date": "2020-01-04"})  # a Saturday
        conn.executemany(
            "INSERT INTO fx_rates(currency, date, per_eur, source)"
            " VALUES (?,?,?,?)",
            [("AUD", "2020-01-03", 1.6, "EODHD"),
             ("AUD", "2020-01-06", 1.7, "EODHD")])
        build_db._apply_fx_rates(conn)
        row = conn.execute(
            "SELECT fx_rate, fx_target_currency, fx_rate_date FROM lots"
        ).fetchone()
        self.assertEqual(row, (1.6, "EUR", "2020-01-03"))
        conn.close()

    def test_apply_fx_rates_no_rate_before_coverage_starts(self):
        """A lot dated before the currency's earliest cached rate gets no
        rate -- extrapolating backwards would be a guess, not a lookup."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("langtons", "1", "Langtons 1", None,
                                   "AUD", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x", "currency": "AUD",
                               "lot_date": "1998-01-01"})
        conn.execute(
            "INSERT INTO fx_rates(currency, date, per_eur, source)"
            " VALUES ('AUD', '2006-03-01', 1.6, 'EODHD')")
        build_db._apply_fx_rates(conn)
        row = conn.execute(
            "SELECT fx_rate, fx_target_currency, fx_rate_date FROM lots"
        ).fetchone()
        self.assertEqual(row, (None, None, None))
        conn.close()

    def test_sylvies_premium_is_20_percent_with_no_tax(self):
        """sylvies.be Conditions of Sale: 20% buyer's premium excl. VAT, no
        per-lot fee, VAT is destination-dependent (no single numeric rate) --
        same treatment as sothebys/langtons/christies: tax_amount stays NULL."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("sylvies", "1", "Sylvies 1", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "hammer_price": 100.0, "price_basis": "HAMMER",
                               "currency": "EUR"})
        build_db._apply_premium_policy(conn)
        build_db._apply_tax(conn)
        row = conn.execute(
            "SELECT buyer_premium, fees, tax_amount, total_price, price_source"
            " FROM lots").fetchone()
        self.assertEqual(row, (20.0, None, None, 120.0, "DERIVED"))
        conn.close()

    def test_fill_lot_date(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", "2026-01-31",
                                   "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "lot_date": "2026-01-30"})
        builder.add_lot(a_id, {"lot_no": "2", "wine": "y"})
        build_db._fill_lot_date(conn)
        rows = conn.execute(
            "SELECT lot_no, lot_date FROM lots ORDER BY lot_no").fetchall()
        self.assertEqual(rows, [("1", "2026-01-30"), ("2", "2026-01-31")])
        conn.close()

    def test_langtons(self):
        data = {"auction": {"id": "8212", "name": "Unreserved", "date": None},
                "lots": [{"lot": "1", "wine": "Penfolds Grange",
                          "region": "South Australia", "classification": None,
                          "vintage": "2019", "quantity": "1",
                          "winning_bid": 850.0, "currency": "AUD",
                          "notes": None}]}
        count, hammer, wine = _run_loader(
            "Langtons", "8212.json", data, "load_langtons")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_winefields(self):
        data = {"auction": {"auction_id": "1-AO56VE", "title": "WF83",
                            "time_start": "2026-09-22T16:00:00Z"},
                "lots": [{"lot_no": 1, "title": "Marsannay Rouge",
                          "producer": None, "quantity": 6, "size": None,
                          "estimate_low": "160.00", "estimate_high": "220.00",
                          "hammer": "200.00", "status": "sold",
                          "is_mixed_lot": False, "condition": None,
                          "currency": "EUR"}]}
        count, hammer, wine = _run_loader(
            "Winefields", "1-AO56VE.json", data, "load_winefields")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_dorotheum(self):
        data = {"auction": {"id": "127195", "name": None, "date": None},
                "lots": [{"lot_nr": "139-1", "name": "Château Mouton",
                          "estimate": 800.0, "realized_price": 400.0,
                          "sold": 1, "currency": "EUR",
                          "description": None}]}
        count, hammer, wine = _run_loader(
            "Dorotheum", "127195.json", data, "load_dorotheum")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_pandolfini(self):
        data = {"auction": {"id": "1448", "name": "Smartwine",
                            "date": "2026-04-08"},
                "lots": [{"lot_nr": 1, "name": "Ruinart",
                          "estimate_low": None, "estimate_high": None,
                          "sold_price": {"class": "venduto", "value": 20},
                          "description": "Champagne"}]}
        count, _hammer, wine = _run_loader(
            "Pandolfini", "1448.json", data, "load_pandolfini")
        self.assertEqual((count, wine), (1, 1))

    def test_sothebys(self):
        data = {"auction": {"auction_id": "d19bbb8e-71c4-42b9-aba5-366d311806a9",
                            "title": "Live from The Macallan Estate",
                            "dates": "2026-10-09T14:57:00Z",
                            "currency": "GBP", "location": "London"},
                "lots": [{"lot_number": "1", "title": "The Macallan 42.6",
                          "estimate_low": "60000", "estimate_high": "100000",
                          "hammer_price": "140000", "final_price": 175000.0,
                          "sold": 1, "currency": "GBP"}]}
        count, hammer, wine = _run_loader(
            "Sothebys", "l26722.json", data, "load_sothebys")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_finarte(self):
        data = {"auction": {"slug": "fine-wines-16", "name": None,
                            "date": None},
                "lots": [{"lot_nr": "1", "name": "Gaja (1 BT)",
                          "region": "Barbaresco", "vintage": "1981",
                          "estimate_min": "180", "estimate_max": "220",
                          "hammer_price": 221.4, "sold": 1,
                          "currency": "EUR", "vat_regime": "RF15"}]}
        count, hammer, wine = _run_loader(
            "Finarte", "16.json", data, "load_finarte")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_beschcannes(self):
        data = {"auction": {"id": "408", "slug": "408-x", "date": None,
                            "currency": "EUR", "price_basis": "HAMMER"},
                "lots": [{"lot_no": "401", "appellation": "Dom Perignon",
                          "vintage": "1973", "estimate": [1000.0, 1500.0],
                          "adjuge": 2650.0, "description": "1 Bouteille",
                          "remarks": None}]}
        count, hammer, wine = _run_loader(
            "BeschCannes", "auction-408.json", data, "load_beschcannes")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_christies(self):
        data = {"auction": {"event_id": "31122", "title": "Henry Tang",
                            "year": 2026, "month": 10,
                            "landing_url": "https://www.christies.com/en/"
                                           "auction/auction-31122",
                            "location": "HongKong"},
                "lots": [{"lot_number": "1",
                          "title": "Château Lafite Rothschild 1953",
                          "estimate_low": 70000.0, "estimate_high": 100000.0,
                          "price_realised": 118750.0, "lot_withdrawn": False,
                          "currency": "HKD", "description": "1 Magnum",
                          "url": "https://www.christies.com/en/lot/lot-6604342"}]}
        count, hammer, wine = _run_loader(
            "Christies", "31122.json", data, "load_christies")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_koppe(self):
        data = {"auction": {"id": "10", "name": "Koppe 10", "date": None},
                "lots": [{"lot_no": "1", "name": "Chateau Haut-Brion",
                          "region": "Pessac-Leognan", "vintage": "1998",
                          "color": "Rot", "bottle_size": "6,0 l",
                          "format": ["1 Imperial"],
                          "hammer_price": 6000.0}]}
        count, hammer, wine = _run_loader(
            "Koppe", "10.json", data, "load_koppe")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_weinboerse(self):
        # Real shape (not the old weinauktion-platform API this loader used
        # to assume): a paginated export where each page embeds its own
        # slice of the auction/catalog/part graph under "@related", and
        # the lot description is one HTML blob to parse, not structured
        # fields.
        data = {
            "@related": {
                "auctions": [{"id": 1, "title": "Auktion 102",
                              "startDate": "2020-11-14T00:00:00+00:00",
                              "currency": "CHF"}],
                "catalogs": [{"id": 1, "auctionId": 1}],
                "parts": [{"id": 1, "auctionCatalogId": 1}],
            },
            "items": [
                {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                 "description": ("Burgund rot / DOMAINE DUJAC<br />"
                                  "Clos de la Roche gr.c., OHK<br />"
                                  "Jahrgang: 2011<br /><b>3 Flaschen</b>"
                                  "<br /><br /><b>Schätzpreis: 420 - 600 "
                                  "CHF</b>"),
                 "basePrice": 420, "upperBasePrice": 600,
                 "hammerPrice": 540, "state": "sold"},
            ],
        }
        count, hammer, wine = _run_loader(
            "Weinboerse", "Resultfile1.json", data, "load_weinboerse")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_weinboerse_fields(self):
        """Producer/vintage/quantity/size/OHK all come out of the blob."""
        data = {
            "@related": {
                "auctions": [{"id": 1, "title": "Auktion 102",
                              "startDate": "2020-11-14T00:00:00+00:00",
                              "currency": "CHF"}],
                "catalogs": [{"id": 1, "auctionId": 1}],
                "parts": [{"id": 1, "auctionCatalogId": 1}],
            },
            "items": [
                {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                 "description": ("Burgund rot / DOMAINE DUJAC<br />"
                                  "Clos de la Roche gr.c., OHK<br />"
                                  "Jahrgang: 2011<br /><b>3 Flaschen</b>"
                                  "<br /><br /><b>Schätzpreis: 420 - 600 "
                                  "CHF</b>"),
                 "basePrice": 420, "upperBasePrice": 600,
                 "hammerPrice": 540, "state": "sold"},
            ],
        }
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Weinboerse"), exist_ok=True)
            with open(os.path.join(d, "Weinboerse", "Resultfile1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_weinboerse(builder, None)
            finally:
                build_db.ARCHIVE = old
            row = conn.execute(
                "SELECT wine, producer, vintage, quantity, bottle_size_dl,"
                " is_ohk, hammer_price, currency, region, color"
                " FROM lots").fetchone()
            conn.close()
        self.assertEqual(row, ("Clos de la Roche gr.c.", "DOMAINE DUJAC",
                               2011, 3, 7.5, 1, 540.0, "CHF", "Burgund",
                               "Rot"))

    def test_weinboerse_also_loads_ci_fetcher_output(self):
        """Going forward, the CI WeinauktionFetcher writes NEW auctions to
        the lowercase "weinboerse/<id>.json" dir in the simpler {auction,
        lots} shape (ingest/fetchers/weinauktion.py) -- a different
        directory from the historical "Weinboerse/**/Resultfile*.json"
        dump this loader primarily reads. Both must end up loaded."""
        data = {"auction": {"id": "627", "name": "eAuktion 116",
                            "date": "2026-01-31", "currency": "CHF"},
                "lots": [{"lot_no": "1", "wine": "Barolo 2015",
                          "vintage": "2015", "estimate_low": 20.0,
                          "estimate_high": 40.0, "hammer_price": 34.0,
                          "sold": 1, "currency": "CHF"}]}
        count, hammer, wine = _run_loader(
            "weinboerse", "627.json", data, "load_weinboerse")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_weinboerse_dedupes_rescraped_pages(self):
        """Same (partId, id) key repeated byte-for-byte across pages (a
        known re-scrape artifact, confirmed on the real archive) must only
        load once, not once per occurrence."""
        item = {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                "description": ("Burgund rot / DOMAINE DUJAC<br />"
                                 "Clos de la Roche gr.c.<br />"
                                 "Jahrgang: 2011<br /><b>3 Flaschen</b>"),
                "basePrice": 420, "upperBasePrice": 600,
                "hammerPrice": 540, "state": "sold"}
        related = {"auctions": [{"id": 1, "title": "Auktion 102",
                                 "startDate": "2020-11-14T00:00:00+00:00",
                                 "currency": "CHF"}],
                   "catalogs": [{"id": 1, "auctionId": 1}],
                   "parts": [{"id": 1, "auctionCatalogId": 1}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Weinboerse"), exist_ok=True)
            for n in (1, 2, 3):
                with open(os.path.join(d, "Weinboerse",
                                       f"Resultfile{n}.json"),
                          "w", encoding="utf-8") as fh:
                    json.dump({"@related": related, "items": [item]}, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_weinboerse(builder, None)
            finally:
                build_db.ARCHIVE = old
            count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
            conn.close()
        self.assertEqual(count, 1)

    def test_sylvies_txt_dedupes_a_block_repeated_within_one_file(self):
        """A lot block repeated once inside an otherwise-unique file (a
        page re-fetched on retry, printed twice -- confirmed on the real
        archive: lot 1972 in 2018/May20218.txt) must only load once."""
        block = ("\nLot Number: 1\nLot Name: 2007 Some Wine\n"
                 "Lot Description: 1er Cru | Someone\n"
                 "Lot Bottle: 3 Bottle\nLot Bottletype: \n"
                 "Estimate: € 130 - € 180\nResult: € 170\n"
                 "Lot My Bid: N/A\n")
        text = block + "-" * 40 + block
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sylvies"), exist_ok=True)
            with open(os.path.join(d, "sylvies", "March2030.txt"),
                      "w", encoding="utf-8") as fh:
                fh.write(text)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_sylvies_txt(builder, None)
            finally:
                build_db.ARCHIVE = old
            count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
            conn.close()
        self.assertEqual(count, 1)

    def test_weinboerse_fetcher_output_supersedes_historical_dump(self):
        """Once the CI fetcher has written its own file for a catalog, the
        frozen historical dump's copy of that SAME auction must be
        skipped -- not double-loaded on top of it. Catalog ids don't
        cleanly partition from this dump's auction ids (168->167 etc. on
        the real archive), so this has to be checked, not assumed."""
        item = {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                "description": ("Burgund rot / DOMAINE DUJAC<br />"
                                 "Clos de la Roche gr.c.<br />"
                                 "Jahrgang: 2011<br /><b>3 Flaschen</b>"),
                "basePrice": 420, "upperBasePrice": 600,
                "hammerPrice": 540, "state": "sold"}
        related = {"auctions": [{"id": 1, "title": "Auktion 102",
                                 "startDate": "2020-11-14T00:00:00+00:00",
                                 "currency": "CHF"}],
                   "catalogs": [{"id": 1, "auctionId": 1}],
                   "parts": [{"id": 1, "auctionCatalogId": 1}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Weinboerse"), exist_ok=True)
            with open(os.path.join(d, "Weinboerse", "Resultfile1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"@related": related, "items": [item]}, fh)
            # The fetcher's own output for catalog id 1 -- filename is the
            # catalog id (see data/orchestrate.py's default `_filename`).
            with open(os.path.join(d, "Weinboerse", "1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({
                    "auction": {"id": "1", "name": "Auktion 102",
                               "date": "2020-11-14", "currency": "CHF"},
                    "lots": [{"lot_no": "1", "wine": "Clos de la Roche",
                             "hammer_price": 540.0, "sold": 1,
                             "currency": "CHF"}],
                }, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_weinboerse(builder, None)
            finally:
                build_db.ARCHIVE = old
            count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
            conn.close()
        self.assertEqual(count, 1)

    def test_load_weinauktion_json_skips_phantom_auction_files(self):
        """A raw '@related'/'items'-shaped file (this house's own export,
        not a run_ingest.py fetch) must not create a phantom auction with
        id "None" -- that was the exact mechanism behind the original
        "1 auction / 0 lots" weinboerse bug."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "weinboerse"), exist_ok=True)
            with open(os.path.join(d, "weinboerse", "Resultfile1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"@related": {}, "items": []}, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db._load_weinauktion_json(builder, "weinboerse", None)
            finally:
                build_db.ARCHIVE = old
            n_auctions = conn.execute(
                "SELECT COUNT(*) FROM auctions").fetchone()[0]
            conn.close()
        self.assertEqual(n_auctions, 0)

    def test_weinauktionator(self):
        # Real shape (data/parse_results.py::parse_weinauktionator_xlsx's
        # actual output, verified against all 30 archived xlsx files) --
        # auction.id is always None; load_weinauktionator derives the real
        # id from the filename ("results_<id>") instead.
        data = {
            "auction": {"id": None, "name": "Auktionsergebnisse: Test",
                       "date": "2021-08-01", "source": "weinauktionator"},
            "lots": [{"lot_no": "01868", "region": "Bordeaux",
                      "wine": "Château Cheval Blanc, Ch. Cheval Blanc 1976",
                      "hammer_price": 250.0,
                      "format": "1 x 0.750 Château Cheval Blanc, "
                                "Ch. Cheval Blanc 1976"}],
        }
        count, hammer, wine = _run_loader(
            "weinauktionator", "weinauktionator_results_8.json", data,
            "load_weinauktionator")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_christies_prefers_the_richer_year_month_subfolder_file(self):
        """The archive keeps both the original flat-path scrape and a
        later, richer re-scrape of the SAME sale under a year/month
        subfolder (exact date_display, sale_total) -- not two different
        auctions. Confirmed on real sale 20043: identical lot content,
        the subfolder copy just has more metadata. Only one must load."""
        old = {"auction": {"event_id": "20043", "title": "Fine and Rare "
                           "Wines", "year": 2006, "month": 3,
                           "location": "NewYork"},
               "lots": [{"lot_number": "1", "title": "Dom Pérignon",
                         "price_realised": "1292.0", "currency": "USD",
                         "lot_withdrawn": False}]}
        new = {"auction": {"event_id": "20043", "title": "Fine and Rare "
                           "Wines", "year": 2006, "month": 3,
                           "location": "New York", "date_display":
                           "11 March"},
               "lots": [{"lot_number": "1", "title": "Dom Pérignon",
                         "price_realised": "1292.0", "currency": "USD",
                         "lot_withdrawn": False}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Christies", "2006", "03_März"),
                       exist_ok=True)
            with open(os.path.join(d, "Christies", "20043.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(old, fh)
            with open(os.path.join(d, "Christies", "2006", "03_März",
                                   "20043.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(new, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old_archive = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_christies(builder, None)
            finally:
                build_db.ARCHIVE = old_archive
            count = conn.execute("SELECT COUNT(*) FROM lots").fetchone()[0]
            location, date = conn.execute(
                "SELECT location, auction_date FROM auctions").fetchone()
            conn.close()
        self.assertEqual(count, 1)
        self.assertEqual(location, "New York")
        self.assertEqual(date, "2006-03-11")

    def test_christies_nlg_premium_rate_not_the_flat_25_percent(self):
        """Historic NLG (pre-euro Amsterdam) lots used 20.825%, not the
        25% wine rate -- 6,188 lots in the real archive carry currency
        'NLG' and were silently getting the wrong rate."""
        data = {"auction": {"event_id": "1", "title": "t", "year": 1995,
                            "month": 1},
                "lots": [{"lot_number": "1", "title": "Wine",
                          "price_realised": "936.0", "currency": "NLG",
                          "lot_withdrawn": False}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Christies"), exist_ok=True)
            with open(os.path.join(d, "Christies", "1.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(data, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_christies(builder, None)
            finally:
                build_db.ARCHIVE = old
            hammer = conn.execute(
                "SELECT hammer_price FROM lots").fetchone()[0]
            conn.close()
        self.assertEqual(hammer, 774.67)  # 936 / 1.20825, not / 1.25

    def test_dobiaschofsky(self):
        data = {"auction": {"id": "wein", "name": None, "date": None},
                "lots": [{"lot_nr": "12550", "name": "Domaine de la Romanee",
                          "vintage": "1986", "estimate_chf": None,
                          "hammer_chf": 10000.0,
                          "description": "Romanee Conti"}]}
        count, hammer, wine = _run_loader(
            "Dobiaschofsky", "auktion-wein.json", data, "load_dobiaschofsky")
        self.assertEqual((count, hammer, wine), (1, 1, 1))

    def test_steinfels_staging_dedupes_exact_row_repeats(self):
        """Confirmed real case: the 04.05.2002 sheet in
        vinoStagingFileSteinfels.xlsx repeats some lots' rows verbatim
        11-12 times (a transcription artifact in that one worksheet, not
        a loader bug -- one sheet, read once). The loader keeps only the
        first occurrence per (lot_no, wine, vintage, quantity, region,
        price) and leaves a genuinely different row sharing a lot_no
        alone."""
        import openpyxl

        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "data"), exist_ok=True)
            path = os.path.join(d, "data", "vinoStagingFileSteinfels.xlsx")
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Steinfels_04.05.2002"
            header = ["name", "origin", "producer", "region", "vintage",
                      "deciliters", "eventIdentifier", "isOHK", "noOfBottles",
                      "providerOfferingId", "note", "offeringDate",
                      "priceMin", "priceMax", "realizedPrice", "provider"]
            ws.append(header)
            repeated = ["Pommard", "null", "null", "null", "1970", "7.5",
                        "null", "true", "12", "248", "null", "04.05.2002",
                        "null", "null", "0", "Steinfels"]
            for _ in range(11):
                ws.append(repeated)
            distinct_same_lot_no = ["Chambertin", "null", "null", "null",
                                     "1983", "7.5", "null", "true", "4",
                                     "248", "null", "04.05.2002", "null",
                                     "null", "460", "Steinfels"]
            ws.append(distinct_same_lot_no)
            wb.save(path)

            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old_repo = build_db.REPO
            build_db.REPO = d
            try:
                build_db.load_steinfels_staging(builder, None)
            finally:
                build_db.REPO = old_repo
            conn.commit()
            rows = conn.execute(
                "SELECT wine, hammer_price FROM lots ORDER BY wine"
            ).fetchall()
            conn.close()
        self.assertEqual(
            rows, [("Chambertin", 460.0), ("Pommard", 0.0)])

    def test_steinfels_resultfile_json_parses_historical_dump(self):
        """The historical raw export of the weinauktion platform's own
        paginated API response (confirmed: 3,904 files, 2016-2026) --
        same shape load_weinboerse already handles, but steinfels never
        had an equivalent loader at all, which is why its data looked
        "frozen since 2016" (the house itself is very much still
        running -- "eAuktion 125" as of 2026-11-01)."""
        item = {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                "shortDescription": "", "description": "Château X, 2015",
                "basePrice": 100, "upperBasePrice": 180,
                "hammerPrice": 150, "state": "sold"}
        related = {"auctions": [{"id": 408, "title": "Auktion 408",
                                 "startDate": "2023-06-09T08:00:00+00:00",
                                 "currency": "CHF"}],
                   "catalogs": [{"id": 1, "auctionId": 408}],
                   "parts": [{"id": 1, "auctionCatalogId": 1}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Steinfels"), exist_ok=True)
            with open(os.path.join(d, "Steinfels", "Resultfile1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"@related": related, "items": [item]}, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db._load_steinfels_resultfile_json(builder, None)
            finally:
                build_db.ARCHIVE = old
            row = conn.execute(
                "SELECT a.auction_id, a.title, l.lot_no, l.wine, l.vintage,"
                " l.estimate_low, l.estimate_high, l.hammer_price, l.sold"
                " FROM lots l JOIN auctions a ON l.auction_id=a.id").fetchone()
            conn.close()
        self.assertEqual(row, ("api-408", "Auktion 408", "1",
                               "Château X, 2015", 2015, 100.0, 180.0,
                               150.0, 1))

    def test_steinfels_resultfile_json_zero_is_not_a_real_estimate(self):
        """Confirmed real case: upperBasePrice is exactly 0.0 for 26% of
        a random sample of real items, always paired with
        basePrice == startingBid -- a null sentinel (no estimate was
        ever entered), not a genuine CHF-0 estimate."""
        item = {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                "description": "Some wine", "basePrice": 10,
                "upperBasePrice": 0, "startingBid": 10,
                "hammerPrice": 62, "state": "sold"}
        related = {"auctions": [{"id": 8, "title": "eAuktion 8",
                                 "startDate": "2017-01-31T00:00:00+00:00",
                                 "currency": "CHF"}],
                   "catalogs": [{"id": 1, "auctionId": 8}],
                   "parts": [{"id": 1, "auctionCatalogId": 1}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Steinfels"), exist_ok=True)
            with open(os.path.join(d, "Steinfels", "Resultfile1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"@related": related, "items": [item]}, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db._load_steinfels_resultfile_json(builder, None)
            finally:
                build_db.ARCHIVE = old
            row = conn.execute(
                "SELECT estimate_low, estimate_high FROM lots").fetchone()
            conn.close()
        self.assertEqual(row, (10.0, None))

    def test_steinfels_api_auction_id_does_not_collide_with_xlsx_aid(self):
        """Confirmed real case: the platform's own auction id (e.g. 321,
        a 2023-era sale) can coincidentally equal the unrelated
        sequential file number of a 2002-03 XLSX batch file
        (results_321.xlsx) -- without the aid_prefix, both landed under
        one auction_id "321" and merged unrelated lots together under
        duplicate lot numbers."""
        item = {"id": 1, "auctionCatalogPartId": 1, "number": "1",
                "description": "Unrelated 2023 wine", "basePrice": 100,
                "upperBasePrice": 150, "hammerPrice": 120, "state": "sold"}
        related = {"auctions": [{"id": 321, "title": "eAuktion 89",
                                 "startDate": "2023-01-01T00:00:00+00:00",
                                 "currency": "CHF"}],
                   "catalogs": [{"id": 1, "auctionId": 321}],
                   "parts": [{"id": 1, "auctionCatalogId": 1}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Steinfels"), exist_ok=True)
            with open(os.path.join(d, "Steinfels", "Resultfile1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({"@related": related, "items": [item]}, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            # The XLSX-sourced auction, same bare auction_id "321".
            builder.add_auction("steinfels", "321", "321", "2003-01-01",
                               "CHF", "HAMMER")
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db._load_steinfels_resultfile_json(builder, None)
            finally:
                build_db.ARCHIVE = old
            auction_ids = {r[0] for r in conn.execute(
                "SELECT auction_id FROM auctions")}
            conn.close()
        self.assertEqual(auction_ids, {"321", "api-321"})

    def test_zacky_prefers_sale_no_over_colliding_wayback_id(self):
        """Confirmed real case: the wayback-generation archive (id 19-287,
        Zachys' own auctionid) and the later, richer "structured"
        generation (its own small sequential id, 56-169, plus a stable
        sale_no) collide on id "72" for 87 of 97 structured files --
        two unrelated real auctions get merged into one. sale_no is
        unique and never collides with a wayback id; preferring it keeps
        the two auctions apart."""
        wayback = {"auction": {"id": 72, "name": "zCollections, June",
                                "source": "wayback", "year": 2020,
                                "month": 6},
                   "lots": [{"lot_no": "1", "name": "Ausone 2000",
                             "final_price": 930.0}]}
        structured = {"auction": {"id": 72, "name": "zCollections, August",
                                   "sale_no": "2409i"},
                      "lots": [{"lot_no": "1", "name": "Cheval Blanc 1970",
                                "final_price": 300.0}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "Zacky"), exist_ok=True)
            with open(os.path.join(d, "Zacky", "auction-72-old.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(wayback, fh)
            with open(os.path.join(d, "Zacky", "auction-72-new.json"), "w",
                      encoding="utf-8") as fh:
                json.dump(structured, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_zacky(builder, None)
            finally:
                build_db.ARCHIVE = old
            conn.commit()
            rows = conn.execute(
                "SELECT auction_id, title FROM auctions ORDER BY auction_id"
            ).fetchall()
            conn.close()
        self.assertEqual(
            rows, [("2409i", "zCollections, August"),
                   ("72", "zCollections, June")])

    def test_dedupe_munich_lots(self):
        """Confirmed real cases in the MunichWineCompany archive: an
        exact byte-for-byte repeat (auction-111.json lot "81") is
        dropped to one row; a lot scraped both before and after the
        sale closed -- same wine/count_fill/description, one copy with
        price_text="" and hammer_price=None, the other populated
        (auction-89.json lot "101") -- keeps only the populated copy;
        and a reused lot_no that genuinely differs (auction-65.json's
        "9999" catch-all across four unrelated wines) is left alone."""
        exact_dup = {"lot_no": "81", "name": "Pichon Baron", "count_fill": "3",
                     "description": "d", "hammer_price": 490.0,
                     "price_text": "x"}
        before_close = {"lot_no": "101", "name": "Pichon Baron 1989",
                         "count_fill": "3", "description": "d",
                         "hammer_price": None, "price_text": ""}
        after_close = {"lot_no": "101", "name": "Pichon Baron 1989",
                        "count_fill": "3", "description": "d",
                        "hammer_price": 440.0, "price_text": "x"}
        sentinel_a = {"lot_no": "9999", "name": "Wine A", "count_fill": "1",
                      "description": "a", "hammer_price": 50.0}
        sentinel_b = {"lot_no": "9999", "name": "Wine B", "count_fill": "6",
                      "description": "b", "hammer_price": 80.0}
        deduped = build_db._dedupe_munich_lots(
            [exact_dup, dict(exact_dup), before_close, after_close,
             sentinel_a, sentinel_b])
        self.assertEqual(len(deduped), 4)
        lot_101 = [l for l in deduped if l["lot_no"] == "101"]
        self.assertEqual(lot_101, [after_close])
        lot_9999 = [l for l in deduped if l["lot_no"] == "9999"]
        self.assertEqual(len(lot_9999), 2)

    def test_resolve_christies_ditto_lots(self):
        """Confirmed real case: auction 10025 (2000/01_Januar) lot 11 is
        "Armagnac--Vintage 1982" (Chateau de Lacaze); lots 12-14 are each
        literally "1 ^,,^^,,^" (Christie's own ditto-mark convention for
        "same wine as above", kept as literal glyphs by the scrape). Also
        confirmed: auction 5689 (1998/02_Februar) uses an outright empty
        title for the same convention (lot 169 after "Cote de Beaune.
        Ramonet"). Both styles must inherit the nearest preceding lot
        that actually has letters in its title; a ditto lot must never
        become the new reference for lots after it."""
        real_11 = {"lot_number": "11", "title": "Armagnac--Vintage 1982",
                   "description": "Armagnac--Vintage 1982 1 dozen bottles",
                   "price_realised": "100.0"}
        ditto_12 = {"lot_number": "12", "title": "1 ^,,^^,,^",
                    "description": "1 ^,,^^,,^", "price_realised": "90.0"}
        ditto_13 = {"lot_number": "13", "title": "1 ^,,^^,,^",
                    "description": "1 ^,,^^,,^", "price_realised": "80.0"}
        real_16 = {"lot_number": "16", "title": "Eau de Vie",
                   "description": "Eau de Vie 2 bottles",
                   "price_realised": "70.0"}
        empty_17 = {"lot_number": "17", "title": "",
                    "description": "Above 4 bottles per lot",
                    "price_realised": "60.0"}
        resolved = build_db._resolve_christies_ditto_lots(
            [real_11, ditto_12, ditto_13, real_16, empty_17])
        titles = [l["title"] for l in resolved]
        self.assertEqual(titles, ["Armagnac--Vintage 1982"] * 3
                          + ["Eau de Vie"] * 2)
        self.assertEqual(resolved[1]["description"],
                          "Armagnac--Vintage 1982 1 dozen bottles")
        # The lot's own price is never touched by the inheritance.
        self.assertEqual(resolved[1]["price_realised"], "90.0")

    def test_resolve_christies_ditto_lots_no_preceding_real_lot(self):
        """A ditto run with nothing real before it (none observed in the
        archive, but possible in principle at the very start of a sale)
        is left untouched -- not a regression, same as before this fix."""
        ditto_only = {"lot_number": "1", "title": "1 ^,,^^,,^",
                      "description": "1 ^,,^^,,^"}
        resolved = build_db._resolve_christies_ditto_lots([ditto_only])
        self.assertEqual(resolved, [ditto_only])

    def test_backfill_wine_ref_uses_alias_key(self):
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO wine_alias_resolutions(scope_key, alias_key,"
            " discriminator_key, wine_id, resolution_status,"
            " resolution_method, confidence, rule_version, reason)"
            " VALUES (?,?,?,?,?,?,?,?,?)",
            ("global", "chambolle musigny francois bertheau", "", 42,
             "RESOLVED", "auto", 1.0, "1.0", "consistent"))
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, lot_kind)"
            " VALUES (1, '1', 'Chambolle-Musigny François Bertheau', 'SINGLE')")
        build_wines._backfill_wine_ref(conn)
        ref = conn.execute("SELECT wine_ref_id FROM lots").fetchone()[0]
        self.assertEqual(ref, 42)
        conn.close()


if __name__ == "__main__":
    unittest.main()
