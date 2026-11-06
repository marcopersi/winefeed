"""Loader roundtrip: a normalized fetcher output must survive its loader.

Feeds the canonical ``{auction, lots}`` shape that each fetcher emits into its
matching ``load_*`` function and asserts the loader actually reads the fields
(no silent NULLs). This guards the fetcher<->loader field-name contract.
"""
import datetime
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


# pylint: disable=protected-access,too-many-public-methods
# -- protected-access: exercising build_db's internal _apply_* /_load_*
# helpers directly is the point of these round-trip tests; a test class
# naturally accumulates one test_ method per case, past any general
# public-method budget.
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

    def test_annotate_fx_fixes_eur_and_nlg(self):
        """D16: EUR gets a fixed fx_rate=1.0 (not NULL), same mechanism as
        NLG's legal pre-euro fix rate -- so stage 0.5's price_eur =
        price_ccy / fx_rate formula needs no EUR special case."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "Koppe 1", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "eur-lot",
                               "currency": "EUR"})
        builder.add_lot(a_id, {"lot_no": "2", "wine": "nlg-lot",
                               "currency": "NLG"})
        builder.add_lot(a_id, {"lot_no": "3", "wine": "usd-lot",
                               "currency": "USD"})
        build_db._annotate_fx(conn)
        rows = dict(conn.execute(
            "SELECT wine, fx_rate FROM lots ORDER BY wine"))
        self.assertEqual(rows["eur-lot"], 1.0)
        self.assertEqual(rows["nlg-lot"], 2.20371)
        self.assertIsNone(rows["usd-lot"])
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
        rate -- extrapolating backwards would be a guess, not a lookup.
        D18: flagged fx_status='MISSING' instead of a silent NULL, since
        this gap (confirmed structural -- EODHD simply has no AUD history
        before 2006-03-01) is exactly what D18 says must not pass through
        unflagged."""
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
            "SELECT fx_rate, fx_target_currency, fx_rate_date, fx_status"
            " FROM lots").fetchone()
        self.assertEqual(row, (None, None, None, "MISSING"))
        conn.close()

    def test_apply_fx_rates_flags_currency_with_no_cache_at_all(self):
        """D18: a currency fetch_fx.py doesn't cover yet (e.g. TWD before
        its cache is fetched, 0.2b) has no row in fx_rates at all -- must
        still be flagged, not silently skipped just because the
        per-currency loop in _apply_fx_rates never iterates it."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("idealwine", "1", "x", None, "TWD",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x", "currency": "TWD",
                               "lot_date": "2020-01-01"})
        build_db._apply_fx_rates(conn)
        row = conn.execute(
            "SELECT fx_rate, fx_status FROM lots").fetchone()
        self.assertEqual(row, (None, "MISSING"))
        conn.close()

    def test_apply_fx_rates_does_not_flag_unknown_currency(self):
        """D18's fx_status is specifically about a known currency with no
        market rate -- a lot with no currency at all is a separate,
        pre-existing data gap (e.g. winebarrel's static dump never records
        one), not an FX lookup failure, and must not be conflated with it
        by getting the same flag."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("winebarrel", "all", "x", None, None,
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "x",
                               "lot_date": "2020-01-01"})
        build_db._apply_fx_rates(conn)
        row = conn.execute(
            "SELECT fx_rate, fx_status FROM lots").fetchone()
        self.assertEqual(row, (None, None))
        conn.close()

    def test_fill_price_per_bottle_basic_eur_and_foreign_currency(self):
        """D1's formula: realised_price / fx_rate / quantity /
        (bottle_size_dl / 7.5). EUR (fx_rate=1.0, D16) needs no special
        case to produce the same result shape as a real conversion."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "eur-lot",
                               "realised_price": 100.0, "quantity": 2,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0})
        builder.add_lot(a_id, {"lot_no": "2", "wine": "aud-lot",
                               "realised_price": 160.0, "quantity": 1,
                               "bottle_size_dl": 15.0, "fx_rate": 1.6})
        build_db._fill_price_per_bottle(conn)
        rows = dict(conn.execute(
            "SELECT wine, price_per_bottle_eur FROM lots"))
        self.assertAlmostEqual(rows["eur-lot"], 50.0)  # 100/1.0/2/(7.5/7.5)
        self.assertAlmostEqual(rows["aud-lot"], 50.0)  # 160/1.6/1/(15/7.5)
        conn.close()

    def test_fill_price_per_bottle_quantity_flags(self):
        """D5.0.5: quantity NULL -> assumed 1 (flagged, still computed);
        quantity=0 -> flagged, NOT computed (division by zero is a data
        error, not a guess to make); quantity>12 -> flagged but still
        computed (likely a case/carton lot -- forecast_input decides
        whether to filter it, not this step); quantity<0 (review fix: a
        data error, same class as quantity=0) -> flagged, NOT computed --
        dividing through would otherwise silently produce a negative
        price_per_bottle_eur, violating this step's own "keine Werte <=
        0" AC the same way an uncaught zero/negative bottle_size_dl or
        realised_price would."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "qty-null",
                               "realised_price": 75.0, "quantity": None,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0})
        builder.add_lot(a_id, {"lot_no": "2", "wine": "qty-zero",
                               "realised_price": 75.0, "quantity": 0,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0})
        builder.add_lot(a_id, {"lot_no": "3", "wine": "qty-24",
                               "realised_price": 1800.0, "quantity": 24,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0})
        builder.add_lot(a_id, {"lot_no": "4", "wine": "qty-negative",
                               "realised_price": 75.0, "quantity": -1,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0})
        build_db._fill_price_per_bottle(conn)
        rows = dict((w, (p, f)) for w, p, f in conn.execute(
            "SELECT wine, price_per_bottle_eur, ppb_flags FROM lots"))
        self.assertEqual(rows["qty-null"], (75.0, "QTY_ASSUMED"))
        self.assertEqual(rows["qty-zero"], (None, "QTY_SUSPECT"))
        self.assertEqual(rows["qty-24"], (75.0, "QTY_SUSPECT"))
        self.assertEqual(rows["qty-negative"], (None, "QTY_SUSPECT"))
        conn.close()

    def test_fill_price_per_bottle_no_premium_policy(self):
        """Confirmed real: winebarrel has no entry in PREMIUM_POLICY, so a
        hammer-only lot there never gets a realised_price -- D1 requires a
        premium-inclusive price, and there's no documented rate to derive
        one, so this must be flagged and left without a price_per_bottle
        rather than silently computed from hammer alone (G3)."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("winebarrel", "all", "x", None, "CHF",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "no-premium",
                               "hammer_price": 100.0})
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, "NO_PREMIUM_POLICY"))
        conn.close()

    def test_fill_price_per_bottle_no_fx_rate_stays_unset(self):
        """D18: a lot flagged fx_status='MISSING' (no market rate to
        convert with) must not get a guessed price_per_bottle_eur --
        there's nothing meaningful ppb_flags could add here either, since
        fx_status already carries that information, so no NO_FX_RATE flag
        is added on top of it."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("langtons", "1", "x", None, "AUD",
                                   "HAMMER")
        lot_id = builder.add_lot(a_id, {"lot_no": "1", "wine": "no-fx",
                               "realised_price": 100.0, "quantity": 1,
                               "bottle_size_dl": 7.5, "fx_rate": None})
        conn.execute("UPDATE lots SET fx_status='MISSING' WHERE id=?",
                     (lot_id,))
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, None))
        conn.close()

    def test_fill_price_per_bottle_flags_fx_rate_missing_without_status(
            self):
        """Review fix: confirmed real gap -- fx_status is only ever set to
        'MISSING' when lot_date IS NOT NULL (D18, _apply_fx_rates); a
        priced lot with a known currency but no lot_date at all (confirmed
        real, single_wine_prices scope: 3,060 wermuth-sa/franzwermuth lots
        in the live DB) has fx_rate IS NULL *and* fx_status IS NULL, so the
        D18 fx_status flag
        does not explain it. Without its own flag this would silently end
        up with no price_per_bottle_eur and no explanation at all -- a G3
        violation. Must get NO_FX_RATE instead."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("wermuth-sa", "1", "x", None, "CHF",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "no-date-no-fx",
                               "realised_price": 100.0, "quantity": 1,
                               "bottle_size_dl": 7.5, "fx_rate": None})
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, "NO_FX_RATE"))
        conn.close()

    def test_fill_price_per_bottle_no_price_at_all_untouched(self):
        """A lot with no price information whatsoever gets no flag either
        -- there is no price question to flag without a price."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "unsold"})
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, None))
        conn.close()

    def test_fill_price_per_bottle_buyer_premium_set_but_no_realised_price(
            self):
        """Review fix: a loader (e.g. bestwineauctions/ackerwines) can set
        buyer_premium directly from source JSON while realised_price stays
        NULL (e.g. a VAT-text parse failure) -- distinct from winebarrel's
        NO_PREMIUM_POLICY case (no premium known at all) and must not be
        conflated with it, nor silently left unflagged (G3)."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("bestwineauctions", "1", "x", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "premium-no-realised",
                               "hammer_price": 100.0, "buyer_premium": 20.0})
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, "NO_REALISED_PRICE"))
        conn.close()

    def test_fill_price_per_bottle_excludes_mixed_lots(self):
        """Review fix: a MIXED lot (several distinct wines sharing one lot
        number, e.g. sylvies -- lot_kind set by _classify_lots before this
        function runs) must not get a price_per_bottle_eur computed from
        one bottle_size_dl, real or _assume_default_bottle_size's 7.5dl
        default -- that would be a meaningless fabricated figure. Flagged
        MIXED_LOT instead, regardless of bottle_size_dl/fx_rate."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, lot_kind,"
            " realised_price, quantity, bottle_size_dl, fx_rate)"
            " VALUES (1, '1', 'Mixed Case', 'MIXED', 300.0, 3, 7.5, 1.0)")
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, "MIXED_LOT"))
        conn.close()

    def test_fill_price_per_bottle_excludes_unknown_lots(self):
        """Gate-G0 review fix: a lot_kind='UNKNOWN' lot (a spirit
        mislabeled as wine, or no wine name at all -- never resolved to
        any wine_ref_id) must not get a price_per_bottle_eur computed
        either, same reasoning as MIXED: it was never even identified as
        one specific wine, so a "per bottle" figure for it is meaningless.
        Before this fix, the guard only checked lot_kind=='MIXED', so
        UNKNOWN fell through into the normal computation below."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, lot_kind,"
            " realised_price, quantity, bottle_size_dl, fx_rate)"
            " VALUES (1, '1', 'Armagnac Lot', 'UNKNOWN', 300.0, 1, 7.5, 1.0)")
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, "UNKNOWN_LOT"))
        conn.close()

    def test_fill_price_per_bottle_flags_non_positive_bottle_size(self):
        """Review fix: bottle_size_dl <= 0 (never produced by parse_dl, but
        several loaders pass a raw archive field through unvalidated) must
        not be divided by -- zero would crash the build, negative would
        silently produce a negative price (violating the step's own
        'keine Werte <= 0' AC). Flagged SIZE_SUSPECT, no price computed."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "zero-size",
                               "realised_price": 100.0, "quantity": 1,
                               "bottle_size_dl": 0.0, "fx_rate": 1.0})
        builder.add_lot(a_id, {"lot_no": "2", "wine": "negative-size",
                               "realised_price": 100.0, "quantity": 1,
                               "bottle_size_dl": -7.5, "fx_rate": 1.0})
        build_db._fill_price_per_bottle(conn)
        rows = dict((w, (p, f)) for w, p, f in conn.execute(
            "SELECT wine, price_per_bottle_eur, ppb_flags FROM lots"))
        self.assertEqual(rows["zero-size"], (None, "SIZE_SUSPECT"))
        self.assertEqual(rows["negative-size"], (None, "SIZE_SUSPECT"))
        conn.close()

    def test_fill_price_per_bottle_flags_zero_price(self):
        """Confirmed real (live DB, re-verified 2026-11-06 after this
        session's wermuth-sa/bottle-format fixes, single_wine_prices
        scope): 66,726 lots, mostly ackerwines, are marked sold=1 with
        hammer_price/realised_price
        literally 0.0 -- not a donated/no-reserve lot (genuine >0 price),
        but a zero-value "sale" that would otherwise divide through to a
        price_per_bottle_eur of exactly 0, violating this step's own
        'keine Werte <= 0' AC. Flagged ZERO_PRICE instead of computed."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("ackerwines", "1", "x", None, "USD",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "zero-price",
                               "realised_price": 0.0, "hammer_price": 0.0,
                               "buyer_premium": 0.0, "quantity": 1,
                               "bottle_size_dl": 7.5, "fx_rate": 1.6,
                               "sold": 1})
        build_db._fill_price_per_bottle(conn)
        row = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots").fetchone()
        self.assertEqual(row, (None, "ZERO_PRICE"))
        conn.close()

    def test_flag_cote_prices_marks_only_idealwine(self):
        """D11: idealwine's recorded price is a cote/valuation, not an
        auction hammer price -- flagged price_kind='COTE'. A different
        house's lot must stay untouched."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("idealwine", "1", "x", None, "EUR",
                                   "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "cote-wine"})
        b_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(b_id, {"lot_no": "1", "wine": "auction-wine"})
        build_db._flag_cote_prices(conn)
        rows = dict(conn.execute("SELECT wine, price_kind FROM lots"))
        self.assertEqual(rows["cote-wine"], "COTE")
        self.assertIsNone(rows["auction-wine"])
        conn.close()

    def test_flag_duplicate_lots_keeps_one_flags_the_rest(self):
        """0.6 Dubletten: reuses _check_duplicate_lot_numbers's own
        definition (same auction_id+lot_no+full content more than once)
        instead of a wine-identity heuristic -- confirmed live that the
        latter false-positives on paginated auctions and genuine same-
        price twin lots (see module docstring). The first occurrence (by
        id) is left alone; later ones get DUP_CANDIDATE appended (not
        overwriting an existing flag). A near-identical row that differs
        in just one field (hammer_price) is a different real lot, not a
        duplicate, and must stay unflagged."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "dup-original",
                               "vintage": 2020, "quantity": 1,
                               "hammer_price": 100.0})
        dup_id = builder.add_lot(a_id, {"lot_no": "1", "wine": "dup-original",
                                        "vintage": 2020, "quantity": 1,
                                        "hammer_price": 100.0})
        # ppb_flags is derived-only (never set via add_lot) -- set it
        # directly to simulate a row _fill_price_per_bottle already
        # flagged, to check DUP_CANDIDATE appends rather than overwrites.
        conn.execute("UPDATE lots SET ppb_flags='QTY_SUSPECT' WHERE id=?",
                     (dup_id,))
        builder.add_lot(a_id, {"lot_no": "2", "wine": "not-a-dup",
                               "vintage": 2020, "quantity": 1,
                               "hammer_price": 999.0})
        build_db._flag_duplicate_lots(conn)
        rows = conn.execute(
            "SELECT wine, ppb_flags FROM lots ORDER BY id").fetchall()
        self.assertEqual(rows, [
            ("dup-original", None),
            ("dup-original", "QTY_SUSPECT,DUP_CANDIDATE"),
            ("not-a-dup", None),
        ])
        conn.close()

    def test_flag_duplicate_lots_after_fill_price_per_bottle_does_not_clobber(
            self):
        """Regression: confirmed live that running _flag_duplicate_lots
        BEFORE _fill_price_per_bottle loses the DUP_CANDIDATE flag again
        -- _fill_price_per_bottle's own UPDATE writes ppb_flags with a
        plain ``=``, replacing the column outright for every row it
        touches (any row with a price), not just appending to it like
        _append_ppb_flag does. main() must call _fill_price_per_bottle
        first, then _flag_duplicate_lots, for every row with both a
        price and a duplicate lot_no to end up correctly flagged with
        both pieces of information."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        builder.add_lot(a_id, {"lot_no": "1", "wine": "dup-priced",
                               "vintage": 2020, "quantity": 1,
                               "hammer_price": 100.0, "realised_price": 100.0,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0,
                               "sold": 1})
        builder.add_lot(a_id, {"lot_no": "1", "wine": "dup-priced",
                               "vintage": 2020, "quantity": 1,
                               "hammer_price": 100.0, "realised_price": 100.0,
                               "bottle_size_dl": 7.5, "fx_rate": 1.0,
                               "sold": 1})
        build_db._fill_price_per_bottle(conn)
        build_db._flag_duplicate_lots(conn)
        rows = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots"
            " ORDER BY id").fetchall()
        self.assertEqual(rows[0], (100.0, None))
        self.assertEqual(rows[1], (100.0, "DUP_CANDIDATE"))
        conn.close()

    def test_flag_price_outliers_needs_five_obs_and_nonzero_mad(self):
        """0.6 Ausreisser: a group needs >= 5 observations before a
        median/MAD z-score means anything, and a MAD of exactly 0 (every
        price identical) has nothing to measure against -- both skipped
        rather than forced into a result. One clear outlier (10x the
        group's price) among 5 otherwise-identical prices gets flagged;
        the 5 normal ones don't."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")

        # price_per_bottle_eur is derived-only (never set via add_lot) --
        # add the lot, then set it directly to simulate
        # _fill_price_per_bottle's own output. _flag_price_outliers reads
        # from single_wine_prices (Gate-G0 fix), so lot_kind/vintage_status/
        # vintage_final must be set too, same convention as 0.7's own
        # fixture helper.
        def _lot(lot_no, wine, vintage, wine_ref_id, price):
            lot_id = builder.add_lot(a_id, {"lot_no": lot_no, "wine": wine,
                                            "vintage": vintage,
                                            "wine_ref_id": wine_ref_id})
            conn.execute(
                "UPDATE lots SET price_per_bottle_eur=?, lot_kind='SINGLE',"
                " vintage_status='STRUCTURED', vintage_final=? WHERE id=?",
                (price, vintage, lot_id))

        # Too-small group (4 obs): never flagged even with an extreme value.
        for i in range(3):
            _lot(str(i), "small-group", 2019, 1, 50.0)
        _lot("99", "small-group", 2019, 1, 5000.0)
        # Zero-MAD group: 5 identical prices, nothing to measure against.
        for i in range(5):
            _lot(f"z{i}", "zero-mad", 2018, 2, 30.0)
        # Real outlier group: 5 normal prices + 1 extreme.
        for i in range(5):
            _lot(f"o{i}", "outlier-group", 2017, 3, 40.0 + i)
        _lot("o99", "outlier-group", 2017, 3, 9000.0)
        build_db._flag_price_outliers(conn)
        flagged = {w for w, f in conn.execute(
            "SELECT wine, ppb_flags FROM lots WHERE ppb_flags IS NOT NULL")}
        self.assertEqual(flagged, {"outlier-group"})
        outlier_rows = conn.execute(
            "SELECT price_per_bottle_eur, ppb_flags FROM lots"
            " WHERE wine='outlier-group'").fetchall()
        self.assertEqual(sum(1 for _, f in outlier_rows if f == "OUTLIER"), 1)
        conn.close()

    def test_flag_price_outliers_excludes_cote_rows_from_the_group(self):
        """Review fix: a price_kind='COTE' row (idealwine's valuation, not
        a competitive sale -- flagged by _flag_cote_prices, which runs
        before this) must not be counted as one of the group's
        observations, and must never itself be flagged OUTLIER: it isn't
        an auction hammer price to begin with, so it has no place in a
        comparison meant to catch unusual auction prices."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")
        iw_id = builder.add_auction("idealwine", "cote", "x", None, "EUR",
                                     None)

        def _lot(auction_id, lot_no, wine, vintage, wine_ref_id, price):
            lot_id = builder.add_lot(auction_id, {
                "lot_no": lot_no, "wine": wine, "vintage": vintage,
                "wine_ref_id": wine_ref_id})
            conn.execute(
                "UPDATE lots SET price_per_bottle_eur=?, lot_kind='SINGLE',"
                " vintage_status='STRUCTURED', vintage_final=? WHERE id=?",
                (price, vintage, lot_id))

        # 5 normal auction prices, same wine_ref_id/vintage as a cote row
        # priced far outside that range -- without the price_kind filter,
        # the cote row alone would still not be >= 5 obs by itself, but it
        # WOULD join the auction group's 5 obs as a 6th, which is enough to
        # risk distorting the group's median/MAD or getting itself flagged.
        for i in range(5):
            _lot(a_id, f"o{i}", "same-wine", 2017, 3, 40.0 + i)
        _lot(iw_id, "cote-1", "same-wine", 2017, 3, 9000.0)
        build_db._flag_cote_prices(conn)
        build_db._flag_price_outliers(conn)
        rows = dict(conn.execute(
            "SELECT lot_no, ppb_flags FROM lots WHERE wine='same-wine'"))
        self.assertIsNone(rows["cote-1"])
        self.assertTrue(all(f is None for lot_no, f in rows.items()
                             if lot_no != "cote-1"))
        conn.close()

    def test_flag_price_outliers_excludes_qty_suspect_from_the_group(self):
        """Gate-G0 review fix: a QTY_SUSPECT row (quantity<=0 or >12,
        likely a case/mixed lot still priced as a single bottle, flagged
        by _fill_price_per_bottle) must not join the comparison group --
        a bulk-lot price is different economics, not a comparable
        single-bottle sale, same reasoning as the COTE exclusion above."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")

        def _lot(lot_no, wine, vintage, wine_ref_id, price, flags=None):
            lot_id = builder.add_lot(a_id, {
                "lot_no": lot_no, "wine": wine, "vintage": vintage,
                "wine_ref_id": wine_ref_id})
            conn.execute(
                "UPDATE lots SET price_per_bottle_eur=?, lot_kind='SINGLE',"
                " vintage_status='STRUCTURED', vintage_final=?, ppb_flags=?"
                " WHERE id=?",
                (price, vintage, flags, lot_id))

        for i in range(5):
            _lot(f"o{i}", "same-wine", 2017, 3, 40.0 + i)
        _lot("bulk", "same-wine", 2017, 3, 9000.0, flags="QTY_SUSPECT")
        build_db._flag_price_outliers(conn)
        rows = dict(conn.execute(
            "SELECT lot_no, ppb_flags FROM lots WHERE wine='same-wine'"))
        self.assertEqual(rows["bulk"], "QTY_SUSPECT")
        self.assertTrue(all(f is None for lot_no, f in rows.items()
                             if lot_no != "bulk"))
        conn.close()

    def test_flag_price_outliers_ignores_rows_with_unreliable_vintage(self):
        """Gate-G0 review fix: grouping used to fall back to the raw
        ``vintage`` column via COALESCE(vintage_final, vintage) whenever
        vintage_final was NULL -- exactly the case for an unreliable
        vintage_status (NV/MV/MISSING/AMBIGUOUS/CONFLICT/INVALID). Reading
        from single_wine_prices (vintage_status IN STRUCTURED/EXTRACTED
        only) means such a row never joins or contaminates a comparison
        group at all, regardless of what its raw vintage column says."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        builder = build_db.Builder(conn)
        a_id = builder.add_auction("koppe", "1", "x", None, "EUR", "HAMMER")

        def _lot(lot_no, vintage, wine_ref_id, price, vintage_status,
                 vintage_final):
            lot_id = builder.add_lot(a_id, {
                "lot_no": lot_no, "wine": "same-wine", "vintage": vintage,
                "wine_ref_id": wine_ref_id})
            conn.execute(
                "UPDATE lots SET price_per_bottle_eur=?, lot_kind='SINGLE',"
                " vintage_status=?, vintage_final=? WHERE id=?",
                (price, vintage_status, vintage_final, lot_id))

        for i in range(5):
            _lot(f"o{i}", 2017, 3, 40.0 + i, "STRUCTURED", 2017)
        # Raw vintage column coincidentally also "2017", but vintage_status
        # is unreliable (vintage_final NULL) -- must not join the group
        # above even though COALESCE(vintage_final, vintage) would read 2017.
        _lot("bad-vintage", 2017, 3, 9000.0, "AMBIGUOUS", None)
        build_db._flag_price_outliers(conn)
        rows = dict(conn.execute(
            "SELECT lot_no, ppb_flags FROM lots WHERE wine_ref_id=3"))
        self.assertIsNone(rows["bad-vintage"])
        self.assertTrue(all(f is None for lot_no, f in rows.items()
                             if lot_no != "bad-vintage"))
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

    def test_load_weinauktion_json_unsold_lot_price_basis_is_unknown(self):
        """Senior-review finding: price_basis was hardcoded to "HAMMER"
        regardless of sold state, unlike every other loader in this file
        ("HAMMER" if sold else "UNKNOWN", e.g. load_koppe/load_dorotheum/
        load_winefields). An unsold lot with no real hammer_price must
        not be marked as if one were observed."""
        data = {"auction": {"id": 1, "name": "Auktion", "date": None,
                            "currency": "CHF"},
                "lots": [{"lot_no": "1", "wine": "x", "hammer_price": None,
                         "sold": False}]}
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "weinboerse"), exist_ok=True)
            with open(os.path.join(d, "weinboerse", "1.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db._load_weinauktion_json(builder, "weinboerse", None)
            finally:
                build_db.ARCHIVE = old
            row = conn.execute(
                "SELECT price_basis, sold FROM lots").fetchone()
            conn.close()
        self.assertEqual(row, ("UNKNOWN", 0))

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

    def test_munich_wine_company_reads_vintage_region_and_estimate(self):
        """Live fetcher output (ingest/fetchers/munichwinecompany.py,
        munichwinecompany.com's rebuilt cms.*.eu API) carries vintage/
        region/estimate fields the old static-dump loader never read --
        must come through, and an unsold lot (hammer_price None) must
        not be mislabeled price_basis=HAMMER."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "MunichWineCompany"), exist_ok=True)
            with open(os.path.join(d, "MunichWineCompany",
                                   "auction-340.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({
                    "auction": {"id": "340", "title": "OA221", "date": None},
                    "lots": [
                        {"lot_no": 3, "name": "Pauillac 1er Cru Classe",
                         "brand": "Ch. Mouton Rothschild", "vintage": "2020",
                         "region": "Bordeaux, Frankreich",
                         "count_fill": "1 Flasche", "hammer_price": "410.00",
                         "estimate_low": 410, "estimate_high": 600},
                        {"lot_no": 4, "name": "Pauillac 1er Cru Classe",
                         "brand": "Ch. Mouton Rothschild", "vintage": "2019",
                         "region": "Bordeaux, Frankreich",
                         "count_fill": "1 Flasche", "hammer_price": None,
                         "estimate_low": 420, "estimate_high": 620},
                    ],
                }, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_munich_wine_company(builder, None)
            finally:
                build_db.ARCHIVE = old
            rows = conn.execute(
                "SELECT lot_no, vintage, region, hammer_price, price_basis,"
                " estimate_low, estimate_high FROM lots ORDER BY lot_no"
            ).fetchall()
            conn.close()
        self.assertEqual(rows, [
            ("3", 2020, "Bordeaux, Frankreich", 410.0, "HAMMER", 410.0,
             600.0),
            ("4", 2019, "Bordeaux, Frankreich", None, "UNKNOWN", 420.0,
             620.0),
        ])

    def test_winebarrel_loads_fetcher_output_alongside_static_dump(self):
        """The static winebarrel_lots.json dump and the live fetcher's
        per-lot "<auction_id>.json" files (ingest/fetchers/winebarrel.py)
        must both load into the same virtual "all" auction, with no
        double-load if the fetcher ever re-covers an id already in the
        static dump."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "winebarrel"), exist_ok=True)
            with open(os.path.join(d, "winebarrel", "winebarrel_lots.json"),
                      "w", encoding="utf-8") as fh:
                json.dump([{"auction_id": 267, "name": "Old Static Lot",
                           "winery": "X", "bottles": 1,
                           "hammer_price": 100.0,
                           "auction_end": "2019-03-29 18:05:05"}], fh)
            # New fetched lot (not in the static dump).
            with open(os.path.join(d, "winebarrel", "4183.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({
                    "auction": {"id": "4183", "name": None, "date": None},
                    "lots": [{"lot_no": "4183", "wine": "New Fetched Lot",
                             "producer": "Y", "quantity": "6",
                             "bottle_size_dl": 7.5, "hammer_price": 360.0,
                             "sold": 1, "auction_end": "2024-03-02",
                             "currency": "CHF"}],
                }, fh)
            # A re-fetch of an id the static dump already covers -- must
            # not be double-loaded.
            with open(os.path.join(d, "winebarrel", "267.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({
                    "auction": {"id": "267", "name": None, "date": None},
                    "lots": [{"lot_no": "267", "wine": "Old Static Lot",
                             "hammer_price": 100.0, "sold": 1}],
                }, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_winebarrel(builder, None)
            finally:
                build_db.ARCHIVE = old
            rows = conn.execute(
                "SELECT lot_no, wine FROM lots ORDER BY lot_no").fetchall()
            conn.close()
        self.assertEqual(rows, [("267", "Old Static Lot"),
                                ("4183", "New Fetched Lot")])

    def test_winebarrel_1970_epoch_placeholder_becomes_null_date(self):
        """D17: confirmed real -- 680 archived lots carry a literal
        "1970-01-01 01:00:00" auction_end placeholder with no other date
        field on the lot and no usable auction_date fallback (winebarrel's
        one virtual "all" auction has none). Must become lot_date=NULL,
        not a parsed-looking-real 1970-01-01, in both the static-dump and
        live-fetcher-output code paths."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "winebarrel"), exist_ok=True)
            with open(os.path.join(d, "winebarrel", "winebarrel_lots.json"),
                      "w", encoding="utf-8") as fh:
                json.dump([{"auction_id": 69, "name": "Static Epoch Lot",
                           "winery": "X", "bottles": 6, "hammer_price": 2290.0,
                           "auction_end": "1970-01-01 01:00:00"}], fh)
            with open(os.path.join(d, "winebarrel", "4184.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({
                    "auction": {"id": "4184", "name": None, "date": None},
                    "lots": [{"lot_no": "4184", "wine": "Fetched Epoch Lot",
                             "hammer_price": 100.0, "sold": 1,
                             "auction_end": "1970-01-01 01:00:00",
                             "currency": "CHF"}],
                }, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_winebarrel(builder, None)
            finally:
                build_db.ARCHIVE = old
            rows = conn.execute(
                "SELECT lot_no, lot_date FROM lots ORDER BY lot_no").fetchall()
            conn.close()
        self.assertEqual(rows, [("4184", None), ("69", None)])

    def test_sylvies_fetched_json_parses_mixed_lot(self):
        """Live fetcher output (ingest/fetchers/sylvies.py): a mixed lot
        (several distinct wines sharing one lot number) must come out
        fully -- the historic txt-captured archive's scraper only ever
        read the first sub-wine (see load_sylvies_txt's module note),
        this source never had that bug."""
        data = {
            "auction": {"id": "253",
                       "name": "All lots in the auction of"
                                " 15 - 17 October 2026"},
            "lots": [{
                "lot_no": "7",
                "subs": [
                    {"name": "1985 Château Grand Puy Ducasse",
                     "description": "Pauillac | Mc",
                     "bottle": "2 Bottle(s)", "bottle_type": "vts"},
                    {"name": "1985 Château la Tour Carnet",
                     "description": "Haut Médoc | Mc",
                     "bottle": "2 Bottle(s)",
                     "bottle_type": "1 neck, 1 vts"},
                ],
                "estimate_text": "€ 320 - € 480",
                "result_text": "€ 340",
            }],
        }
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sylvies"), exist_ok=True)
            with open(os.path.join(d, "sylvies", "253.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_sylvies_fetched(builder, None)
            finally:
                build_db.ARCHIVE = old
            row = conn.execute(
                "SELECT a.auction_id, l.lot_no, l.wine, l.mixed_lot,"
                " l.quantity, l.hammer_price FROM lots l"
                " JOIN auctions a ON l.auction_id=a.id").fetchone()
            conn.close()
        self.assertEqual(row, (
            "sylvies_2026-10", "7",
            "1985 Château Grand Puy Ducasse; 1985 Château la Tour Carnet",
            1, 4, 340.0))

    def test_sylvies_fetched_title_uses_first_month_of_cross_month_span(self):
        """Confirmed real case: a title spanning two months ("31 Aug & 1
        Sep 2012") names the second month (abbreviated) right before
        the year, but the archive's own bucketing convention uses the
        FIRST day's month (the 2012 archive has "August2012.zip", no
        "September2012.zip" for this exact auction) -- must key on
        August, not September."""
        data = {
            "auction": {"id": "149",
                       "name": "All lots in the auction of"
                                " 31 Aug & 1 Sep 2012"},
            "lots": [{"lot_no": "1", "subs": [{"name": "2010 Some Wine"}],
                      "estimate_text": None, "result_text": None}],
        }
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sylvies"), exist_ok=True)
            with open(os.path.join(d, "sylvies", "149.json"),
                      "w", encoding="utf-8") as fh:
                json.dump(data, fh)
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_sylvies_fetched(builder, None)
            finally:
                build_db.ARCHIVE = old
            auction_id = conn.execute(
                "SELECT auction_id FROM auctions").fetchone()[0]
            conn.close()
        self.assertEqual(auction_id, "sylvies_2012-08")

    def test_sylvies_fetched_covers_txt_month_to_avoid_double_load(self):
        """load_sylvies_fetched must run before load_sylvies_txt so the
        shared "sylvies_<year>-<month>" auction_id is already taken --
        _sylvies_html_covered_months then makes load_sylvies_txt skip
        that month instead of double-loading it from the lower-fidelity
        capture (same mechanism as the html-vs-txt dedup it already
        did)."""
        with tempfile.TemporaryDirectory() as d:
            os.makedirs(os.path.join(d, "sylvies"), exist_ok=True)
            with open(os.path.join(d, "sylvies", "253.json"),
                      "w", encoding="utf-8") as fh:
                json.dump({
                    "auction": {"id": "253",
                               "name": "All lots in the auction of"
                                        " 15 - 17 October 2026"},
                    "lots": [{"lot_no": "1",
                             "subs": [{"name": "2020 Some Wine"}],
                             "estimate_text": None, "result_text": None}],
                }, fh)
            with open(os.path.join(d, "sylvies", "October2026.txt"),
                      "w", encoding="utf-8") as fh:
                fh.write("\nLot Number: 1\nLot Name: 2020 Other Wine\n"
                        "Lot Description: \nLot Bottle: 1 Bottle(s)\n"
                        "Lot Bottletype: \nEstimate: \nResult: \n")
            conn = sqlite3.connect(os.path.join(d, "t.sqlite"))
            conn.executescript(build_db.SCHEMA)
            builder = build_db.Builder(conn)
            old = build_db.ARCHIVE
            build_db.ARCHIVE = d
            try:
                build_db.load_sylvies_fetched(builder, None)
                build_db.load_sylvies_txt(builder, None)
            finally:
                build_db.ARCHIVE = old
            auctions = conn.execute(
                "SELECT COUNT(*) FROM auctions WHERE auction_id="
                "'sylvies_2026-10'").fetchone()[0]
            wine = conn.execute(
                "SELECT wine FROM lots").fetchone()[0]
            conn.close()
        self.assertEqual(auctions, 1)
        self.assertEqual(wine, "Some Wine")

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

    def test_parse_bottle_formats_fills_dl_even_when_quantity_already_set(
            self):
        """0.4/D19: confirmed real -- langtons sets quantity on every lot
        itself (often just 1, the common single-bottle case), so the old
        combined "only update if quantity IS NULL" gate silently discarded
        a perfectly good "2 Magnum Set"-style hint sitting in the lot's own
        wine text for 13,155 langtons lots. bottle_size_dl must fill in
        regardless of quantity's own state; quantity itself keeps the more
        conservative original gate (unchanged here: already 1, stays 1)."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, raw_wine, quantity,"
            " lot_kind) VALUES (1, '1',"
            " 'ALKINA Old Quarter Grenache Shiraz Mataro 2 Magnum Set',"
            " 'ALKINA Old Quarter Grenache Shiraz Mataro 2 Magnum Set',"
            " 1, 'SINGLE')")
        build_wines._parse_bottle_formats(conn)
        row = conn.execute(
            "SELECT quantity, bottle_size_dl FROM lots").fetchone()
        self.assertEqual(row, (1, 15.0))
        conn.close()

    def test_parse_bottle_formats_bare_magnum_does_not_fabricate_quantity(
            self):
        """Gate-G0 review fix: parse_bottle_format's bare-word fallback
        (e.g. a trailing "... Magnum" with no leading count, dorotheum's
        own pattern) returns qty=None precisely because no real count was
        found -- quantity must stay NULL (COALESCE no-op), not get
        fabricated to 1. bottle_size_dl must still fill in from the bare
        match. Before this fix, the caller's gate (`if qty is not None`)
        would have silently dropped the dl hint too whenever qty is None,
        since the original bare-word fallback returned qty=1 to work
        around exactly that gate -- this test locks in the real fix
        (decoupled gate) instead of that earlier workaround."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, raw_wine, lot_kind)"
            " VALUES (1, '1',"
            " '2007 Morillon Zieregg, Weingut Tement, 95 Parker-Punkte,"
            " Magnum',"
            " '2007 Morillon Zieregg, Weingut Tement, 95 Parker-Punkte,"
            " Magnum', 'SINGLE')")
        build_wines._parse_bottle_formats(conn)
        row = conn.execute(
            "SELECT quantity, bottle_size_dl FROM lots").fetchone()
        self.assertEqual(row, (None, 15.0))
        conn.close()

    def test_assume_default_bottle_size_flags_the_guess(self):
        """0.4's Default-Regel: a lot with no size hint at all gets a
        standard 750ml bottle assumed -- flagged size_assumed=1 so it's
        never mistaken for a confirmed size. A lot that already has a
        real bottle_size_dl (confirmed or from _parse_bottle_formats) must
        stay untouched and unflagged."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, lot_kind)"
            " VALUES (1, '1', 'No Hint Wine', 'SINGLE')")
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, bottle_size_dl,"
            " lot_kind) VALUES (1, '2', 'Confirmed Magnum', 15.0, 'SINGLE')")
        build_wines._assume_default_bottle_size(conn)
        rows = conn.execute(
            "SELECT wine, bottle_size_dl, size_assumed FROM lots"
            " ORDER BY lot_no").fetchall()
        self.assertEqual(rows, [
            ("No Hint Wine", 7.5, 1),
            ("Confirmed Magnum", 15.0, None),
        ])
        conn.close()

    def test_assume_default_bottle_size_skips_mixed_lot_flag(self):
        """Review fix: a lot_kind='MIXED' row (e.g. sylvies' multi-sub-lot
        groups) sets bottle_size_dl=NULL deliberately -- several distinct
        wines/sizes share one lot number, so there is no single size to
        assume. Defaulting it to 7.5dl here would fabricate a fake
        confirmed-looking size; must stay NULL/unflagged."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, lot_kind)"
            " VALUES (1, '1', 'Mixed Group', 'MIXED')")
        build_wines._assume_default_bottle_size(conn)
        row = conn.execute(
            "SELECT bottle_size_dl, size_assumed FROM lots").fetchone()
        self.assertEqual(row, (None, None))
        conn.close()

    def test_assume_default_bottle_size_skips_unknown_lot(self):
        """Gate-G0 review fix: the guard used to be ``lot_kind <> 'MIXED'``
        (deny-list), which let a lot_kind='UNKNOWN' row (a spirit, or no
        wine name at all -- never identified as one specific wine) through
        the same gap already closed for MIXED. Switched to an allow-list
        (``lot_kind = 'SINGLE'``) so UNKNOWN stays NULL/unflagged too."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, lot_kind)"
            " VALUES (1, '1', 'Armagnac Lot', 'UNKNOWN')")
        build_wines._assume_default_bottle_size(conn)
        row = conn.execute(
            "SELECT bottle_size_dl, size_assumed FROM lots").fetchone()
        self.assertEqual(row, (None, None))
        conn.close()

    def test_assume_default_bottle_size_skips_keyword_evidence_mixed_lot(
            self):
        """Review fix (2nd): the original guard checked the raw provider
        ``mixed_lot`` flag directly, which only covers sylvies-style
        provider-flagged mixed lots -- a lot ``_classify_lots`` itself
        later classifies MIXED via keyword evidence (e.g. a 'mixed case'
        hint in the wine text) never had ``mixed_lot=1`` set at all, so
        the old guard missed it and fabricated a 7.5dl/size_assumed=1
        default anyway (confirmed real: 28,125 such rows in the live DB).
        ``_assume_default_bottle_size`` now runs after ``_classify_lots``
        (``run()`` reordered) and guards on the final ``lot_kind``, which
        covers this case too."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, mixed_lot, lot_kind)"
            " VALUES (1, '1', 'Mixed Case of Bordeaux', NULL, 'MIXED')")
        build_wines._assume_default_bottle_size(conn)
        row = conn.execute(
            "SELECT bottle_size_dl, size_assumed FROM lots").fetchone()
        self.assertEqual(row, (None, None))
        conn.close()

    def test_run_classifies_before_assuming_default_bottle_size(self):
        """End-to-end regression for the reorder: a lot whose wine text
        matches _classify_lots' keyword-evidence rule (no provider
        mixed_lot flag at all) must come out of the full build_wines.run()
        pipeline with lot_kind='MIXED' and bottle_size_dl still NULL, not
        a fabricated 7.5dl default."""
        conn = sqlite3.connect(":memory:")
        conn.executescript(build_db.SCHEMA)
        conn.execute(
            "INSERT INTO lots(auction_id, lot_no, wine, source_lot_key)"
            " VALUES (1, '1', 'Mixed Case Lot', 'k1')")
        build_wines._classify_lots(conn)
        build_wines._assume_default_bottle_size(conn)
        row = conn.execute(
            "SELECT lot_kind, bottle_size_dl, size_assumed FROM lots"
        ).fetchone()
        self.assertEqual(row, ("MIXED", None, None))
        conn.close()


class ParseDlTest(unittest.TestCase):
    def test_double_magnum_is_not_shadowed_by_plain_magnum_check(self):
        """Confirmed real bug: "double magnum" (3L) contains the
        substring "magnum", so checking for a plain magnum first always
        matched before jeroboam/double-magnum could, silently resolving
        every Double Magnum to 15.0 (1.5L) instead of 30.0 -- a 2x
        price-per-bottle error wherever this text appears (e.g.
        load_ackerwines' raw bottleSize field)."""
        self.assertEqual(build_db.parse_dl("double magnum"), 30.0)
        self.assertEqual(build_db.parse_dl("Double Magnum"), 30.0)
        self.assertEqual(build_db.parse_dl("magnum"), 15.0)
        self.assertEqual(build_db.parse_dl("jeroboam"), 30.0)

    def test_bare_number_is_a_direct_dl_value_not_a_count(self):
        """parse_dl's own contract (dorotheum/pandolfini's "size" field,
        baghera's "format" field): a bare number with no unit text IS the
        dl value itself. zacky_bottle_size_dl exists specifically because
        zacky's "quantity" field reuses the same bare-number shape to mean
        something else entirely (a bottle count) -- see its own test
        below -- not because parse_dl itself is wrong here."""
        self.assertEqual(build_db.parse_dl("7.5"), 7.5)
        self.assertEqual(build_db.parse_dl("15"), 15.0)


class ZackyBottleSizeDlTest(unittest.TestCase):
    def test_bare_count_is_not_a_size(self):
        """Confirmed real bug (D19, 2026-11-05): zacky's quantity field is
        "N" when no size is stated at all -- 24,129 lots got
        bottle_size_dl=1.0 from a literal "1" (bottle count, not 0.1L)
        before this fix, via parse_dl's bare-number-is-a-dl-value
        fallback (correct for other callers, wrong for this one field's
        count-or-count+size shape)."""
        for text in ("1", "6", "12", " 3 ", 1, 6):
            self.assertIsNone(build_db.zacky_bottle_size_dl(text), msg=text)

    def test_decimal_bare_count_is_not_a_size(self):
        """Review fix: a decimal-shaped bare count (e.g. "6.0", or a JSON
        float quantity value) must be treated the same as an integer bare
        count -- the original digits-only guard regex missed this shape
        and would have fallen through to parse_dl's bare-number fallback,
        reproducing the D19 bug for it."""
        for text in ("1.0", "6.0", " 3.0 ", 6.0):
            self.assertIsNone(build_db.zacky_bottle_size_dl(text), msg=text)

    def test_count_plus_size_still_parses(self):
        """The common, correctly-handled case: most zacky quantity values
        do carry a real size alongside the count."""
        self.assertEqual(
            build_db.zacky_bottle_size_dl("1 Bottle 750ml"), 7.5)
        self.assertEqual(
            build_db.zacky_bottle_size_dl("1 Magnum 1.5L"), 15.0)
        self.assertEqual(
            build_db.zacky_bottle_size_dl("1 Double Magnum 3L"), 30.0)

    def test_empty_and_none_stay_none(self):
        self.assertIsNone(build_db.zacky_bottle_size_dl(""))
        self.assertIsNone(build_db.zacky_bottle_size_dl(None))


class ForecastInputViewTest(unittest.TestCase):
    """0.7: the forecast_input view -- builds on single_wine_prices
    (lot_kind='SINGLE', wine_ref_id resolved, vintage_status clean),
    applies D14 (sold=1), D11 (no price_kind='COTE'), the 0.6 flags
    (OUTLIER/QTY_SUSPECT/DUP_CANDIDATE excluded), and D15 (series' most
    recent lot_date within 36 months of today)."""

    RECENT = (datetime.date.today() - datetime.timedelta(days=30)
              ).isoformat()
    STALE = (datetime.date.today() - datetime.timedelta(days=40 * 30)
             ).isoformat()

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)
        self.a_id = self.builder.add_auction(
            "koppe", "1", "x", None, "EUR", "HAMMER")
        self._lot_no = 0

    def _add_eligible_lot(self, wine_ref_id=1, vintage_final=2015,
                           bottle_size_dl=7.5, lot_date=None, sold=1,
                           price_kind=None, ppb_flags=None,
                           vintage_status="STRUCTURED", lot_kind="SINGLE"):
        lot_date = lot_date or self.RECENT
        self._lot_no += 1
        lot_id = self.builder.add_lot(self.a_id, {
            "lot_no": str(self._lot_no), "wine": "test-wine",
            "wine_ref_id": wine_ref_id, "bottle_size_dl": bottle_size_dl,
            "lot_date": lot_date, "sold": sold, "hammer_price": 100.0})
        self.conn.execute(
            "UPDATE lots SET lot_kind=?, vintage_status=?, vintage_final=?,"
            " price_per_bottle_eur=100.0, price_kind=?, ppb_flags=?"
            " WHERE id=?",
            (lot_kind, vintage_status, vintage_final, price_kind, ppb_flags,
             lot_id))
        return lot_id

    def _forecast_wine_refs(self):
        return [r[0] for r in self.conn.execute(
            "SELECT wine_ref_id FROM forecast_input")]

    def test_includes_eligible_row(self):
        self._add_eligible_lot(wine_ref_id=1)
        self.assertEqual(self._forecast_wine_refs(), [1])

    def test_excludes_sold_null(self):
        """D14: sold IS NULL (unknown, ~62% of all lots) must not be
        treated as sold -- confirmed real gap in the plan doc's own
        earlier spec text ("sold IS NOT 0"), which is true for NULL too
        under SQL's three-valued logic and would have silently included
        these rows."""
        self._add_eligible_lot(wine_ref_id=1, sold=None)
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_sold_zero(self):
        self._add_eligible_lot(wine_ref_id=1, sold=0)
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_cote_price_kind(self):
        """D11: idealwine's cote/valuation price, even though
        _fill_price_per_bottle computes a price_per_bottle_eur for it
        same as a real sale."""
        self._add_eligible_lot(wine_ref_id=1, price_kind="COTE")
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_outlier_flag(self):
        self._add_eligible_lot(wine_ref_id=1, ppb_flags="OUTLIER")
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_qty_suspect_flag(self):
        self._add_eligible_lot(wine_ref_id=1, ppb_flags="QTY_SUSPECT")
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_dup_candidate_flag(self):
        self._add_eligible_lot(wine_ref_id=1, ppb_flags="DUP_CANDIDATE")
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_keeps_row_with_unrelated_flag(self):
        """A flag from a different concern (e.g. QTY_ASSUMED, a non-
        blocking 0.5 flag) must not be mistaken for one of the three
        excluding flags via a careless substring match."""
        self._add_eligible_lot(wine_ref_id=1, ppb_flags="QTY_ASSUMED")
        self.assertEqual(self._forecast_wine_refs(), [1])

    def test_excludes_lot_date_null(self):
        lot_id = self.builder.add_lot(self.a_id, {
            "lot_no": "1", "wine": "test-wine", "wine_ref_id": 1,
            "bottle_size_dl": 7.5, "lot_date": None, "sold": 1,
            "hammer_price": 100.0})
        self.conn.execute(
            "UPDATE lots SET lot_kind='SINGLE', vintage_status='STRUCTURED',"
            " vintage_final=2015, price_per_bottle_eur=100.0 WHERE id=?",
            (lot_id,))
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_non_structured_vintage_status(self):
        """Inherited from single_wine_prices: an NV/MV/MISSING/AMBIGUOUS/
        CONFLICT/INVALID vintage_status means vintage_final isn't a
        trustworthy series key -- must not land in forecast_input."""
        self._add_eligible_lot(wine_ref_id=1, vintage_status="NV")
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_mixed_lot_kind(self):
        """Inherited from single_wine_prices: lot_kind='MIXED' lots have
        wine_ref_id forced NULL by the schema's own CHECK constraint, so
        they can never reach forecast_input regardless of any flag."""
        lot_id = self.builder.add_lot(self.a_id, {
            "lot_no": "1", "wine": "test-wine", "wine_ref_id": None,
            "bottle_size_dl": 7.5, "lot_date": self.RECENT, "sold": 1,
            "hammer_price": 100.0})
        self.conn.execute(
            "UPDATE lots SET lot_kind='MIXED', vintage_status='STRUCTURED',"
            " vintage_final=2015, price_per_bottle_eur=100.0 WHERE id=?",
            (lot_id,))
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_excludes_stale_series_entirely(self):
        """D15: a series (wine_ref_id, vintage, size_class) whose most
        recent observation is older than 36 months is dropped entirely
        -- including this one row, which IS the stale series' only (and
        therefore most recent) observation."""
        self._add_eligible_lot(wine_ref_id=1, lot_date=self.STALE)
        self.assertEqual(self._forecast_wine_refs(), [])

    def test_keeps_old_row_when_series_has_a_recent_observation(self):
        """D15 is evaluated per SERIES, not per row: an old observation
        stays in forecast_input as long as the same (wine_ref_id,
        vintage, size_class) series has at least one recent one too."""
        self._add_eligible_lot(wine_ref_id=1, lot_date=self.STALE)
        self._add_eligible_lot(wine_ref_id=1, lot_date=self.RECENT)
        self.assertEqual(sorted(self._forecast_wine_refs()), [1, 1])

    def test_different_size_class_is_a_separate_series(self):
        """D10: no cross-size equivalence factor -- a stale 7.5dl series
        and a recent 15.0dl (magnum) series for the same wine_ref_id/
        vintage are independent; the magnum's recency doesn't rescue the
        standard bottle's stale series, and vice versa."""
        self._add_eligible_lot(wine_ref_id=1, bottle_size_dl=7.5,
                               lot_date=self.STALE)
        self._add_eligible_lot(wine_ref_id=1, bottle_size_dl=15.0,
                               lot_date=self.RECENT)
        rows = self.conn.execute(
            "SELECT size_class FROM forecast_input").fetchall()
        self.assertEqual(rows, [(15.0,)])

    def test_flagged_recent_row_still_keeps_series_active(self):
        """Gate-G0 review fix: a series' recency must be judged on ALL real
        sales, not only the ones that also survive the OUTLIER/QTY_SUSPECT/
        DUP_CANDIDATE filter. Setup: an old (stale) UNFLAGGED row that would
        otherwise qualify, plus a RECENT row flagged OUTLIER for the same
        series. The recent row itself must stay excluded (it's flagged),
        but its existence proves the wine is still actively traded, so the
        old row must NOT be dropped as part of a wrongly "inactive" series.
        Before the fix, MAX(lot_date) was computed only over already-
        flag-filtered rows, so the recent OUTLIER row never counted and the
        whole series -- including the old, otherwise-clean row -- was
        silently excluded."""
        old_id = self._add_eligible_lot(wine_ref_id=1, lot_date=self.STALE)
        self._add_eligible_lot(wine_ref_id=1, lot_date=self.RECENT,
                               ppb_flags="OUTLIER")
        rows = self.conn.execute(
            "SELECT lot_id FROM forecast_input").fetchall()
        self.assertEqual(rows, [(old_id,)])

    def tearDown(self):
        self.conn.close()


class WermuthValidatedCsvColumnShiftTest(unittest.TestCase):
    """Gate-G0 sample verification (0.4) found this live: 215 wermuth-sa
    rows across output_WermuthSA_*.csv have 11 columns where column 2
    (origin/classification) is empty and column 3 holds a region string
    instead -- the old content-based ``has_origin`` check (row[2]
    non-empty) misdetected these as 10-column rows, shifting vintage/
    quantity/bottle_size_dl *and the realized price itself* by one
    column. The offset must depend only on column count."""

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)

    def _load(self, rows):
        with tempfile.TemporaryDirectory() as d:
            out_dir = os.path.join(d, "VinoImporter", "validatedOutput")
            os.makedirs(out_dir, exist_ok=True)
            with open(os.path.join(out_dir, "output_WermuthSA_01012020.csv"),
                      "w", encoding="utf-8") as fh:
                fh.write("\n".join(";".join(r) for r in rows) + "\n")
            old_repo = build_db.REPO
            build_db.REPO = d
            try:
                build_db.load_wermuth_validated(self.builder, None)
            finally:
                build_db.REPO = old_repo
        self.conn.commit()
        return self.conn.execute(
            "SELECT vintage, quantity, bottle_size_dl, hammer_price"
            " FROM lots ORDER BY lot_no"
        ).fetchall()

    def test_10_column_row(self):
        rows = self._load([[
            "1", "Chateau A", "null", "2000", "12", "7.5", "true",
            "780", "960", "800"]])
        self.assertEqual(rows, [(2000, 12, 7.5, 800.0)])

    def test_11_column_origin_at_index_2(self):
        rows = self._load([[
            "1", "Wine B", "Producer B", "null", "2000", "12", "7.5",
            "true", "1600", "2000", "1300"]])
        self.assertEqual(rows, [(2000, 12, 7.5, 1300.0)])

    def test_11_column_region_at_index_3_classification_empty(self):
        """The bug case: confirmed live for 70 rows (e.g. lot 28,
        09.09.2017: hammer_price was silently read as 3600 -- the
        estimate_high field -- instead of the real 1700)."""
        rows = self._load([[
            "28", "Chateau La Conseillante", "null", "Pomerol", "2009",
            "12", "7.5", "true", "3000", "3600", "1700"]])
        self.assertEqual(rows, [(2009, 12, 7.5, 1700.0)])

    def test_11_column_both_index_2_and_3_empty(self):
        """Confirmed live for 145 rows (e.g. lot 206, 09.09.2017)."""
        rows = self._load([[
            "206", "Rosso del Bepi", "null", "null", "1999", "1", "7.5",
            "false", "80", "150", "80"]])
        self.assertEqual(rows, [(1999, 1, 7.5, 80.0)])

    def test_11_column_both_index_2_and_3_filled(self):
        rows = self._load([[
            "167", "Chardonnay Boars View", "MO Sonoma", "Schrader Cellars",
            "2014", "6", "7.5", "true", "1620", "1920", "1200"]])
        self.assertEqual(rows, [(2014, 6, 7.5, 1200.0)])

    def test_10_real_columns_plus_trailing_blank_is_not_11_columns(self):
        """Gate-G0 review fix (2nd round, caught by an adversarial
        reviewer re-checking the first fix): a trailing empty field
        (";...;340;") is a CSV artifact, not a real 11th column --
        confirmed live for 2 rows (e.g. lot 313, 14.03.2015: 'Hermitage;
        Chave;2009;11;7.5;false;220;330;340;'). Counting the blank
        toward the length misread this as an 11-column row (off=1,
        vintage read as '11' -- the real quantity), corrupting the same
        fields the first fix was meant to protect. Must strip trailing
        blanks before counting."""
        rows = self._load([[
            "313", "Hermitage", "Chave", "2009", "11", "7.5", "false",
            "220", "330", "340", ""]])
        self.assertEqual(rows, [(2009, 11, 7.5, 340.0)])

    def test_11_real_columns_plus_trailing_blank_still_off_by_one(self):
        """Same trim, opposite direction: a genuinely 11-field row with
        an extra trailing blank (both origin AND producer filled, e.g.
        lot 167/13.03.2018) must still resolve with off=1, not be
        mistaken for a 12-column shape."""
        rows = self._load([[
            "167", "Chardonnay Boars View", "MO Sonoma", "Schrader Cellars",
            "2014", "6", "7.5", "true", "1620", "1920", "1200", ""]])
        self.assertEqual(rows, [(2014, 6, 7.5, 1200.0)])


if __name__ == "__main__":
    unittest.main()
