"""1.2: forecast.data.load_series against a real forecast_input view."""
import datetime
import math
import sqlite3
import unittest

import pandas as pd

import build_db
from forecast import data as fdata


class LoadSeriesTest(unittest.TestCase):
    RECENT = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)
        self.koppe_id = self.builder.add_auction(
            "koppe", "1", "x", None, "EUR", "HAMMER")
        self.langtons_id = self.builder.add_auction(
            "langtons", "1", "x", None, "EUR", "HAMMER")
        self._lot_no = 0

    def _add_lot(self, auction_id, wine_ref_id=1, vintage_final=2015,
                 bottle_size_dl=7.5, lot_date=None, price=100.0, qty=1):
        lot_date = lot_date or self.RECENT
        self._lot_no += 1
        lot_id = self.builder.add_lot(auction_id, {
            "lot_no": str(self._lot_no), "wine": "test-wine",
            "wine_ref_id": wine_ref_id, "bottle_size_dl": bottle_size_dl,
            "quantity": qty, "lot_date": lot_date, "sold": 1,
            "hammer_price": price})
        self.conn.execute(
            "UPDATE lots SET lot_kind='SINGLE', vintage_status='STRUCTURED',"
            " vintage_final=?, price_per_bottle_eur=?, quantity=? WHERE id=?",
            (vintage_final, price, qty, lot_id))
        return lot_id

    def tearDown(self):
        self.conn.close()

    def test_empty_series_returns_empty_frame_with_right_columns(self):
        df = fdata.load_series(self.conn, 999, 2015, 7.5)
        self.assertEqual(len(df), 0)
        self.assertEqual(
            list(df.columns),
            ["date", "y", "provider", "qty", "house_offset"])

    def test_single_row(self):
        self._add_lot(self.koppe_id, price=150.0, qty=2)
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df["y"].iloc[0], math.log(150.0))
        self.assertEqual(df["provider"].iloc[0], "koppe")
        self.assertEqual(df["qty"].iloc[0], 2)

    def test_sorted_by_date_ascending_regardless_of_insertion_order(self):
        # D15 only admits a series whose most recent observation is
        # <= 36 months old -- all three dates must stay within that
        # window (forecast_input, not load_series, enforces this; it is
        # not load_series's own concern, but a test fixture using a
        # stale absolute date would silently hit it and fail for the
        # wrong reason).
        today = datetime.date.today()
        self._add_lot(self.koppe_id, price=300.0,
                      lot_date=(today - datetime.timedelta(days=10)
                               ).isoformat())
        self._add_lot(self.koppe_id, price=100.0,
                      lot_date=(today - datetime.timedelta(days=400)
                               ).isoformat())
        self._add_lot(self.koppe_id, price=200.0,
                      lot_date=(today - datetime.timedelta(days=200)
                               ).isoformat())
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(list(df["date"]), sorted(df["date"]))
        self.assertEqual(
            [round(math.exp(y)) for y in df["y"]], [100, 200, 300])

    def test_same_date_tiebreak_is_deterministic_lot_id_order(self):
        first = self._add_lot(self.koppe_id, price=50.0,
                              lot_date=self.RECENT)
        second = self._add_lot(self.koppe_id, price=60.0,
                               lot_date=self.RECENT)
        self.assertLess(first, second)
        df1 = fdata.load_series(self.conn, 1, 2015, 7.5)
        df2 = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(list(df1["y"]), list(df2["y"]))
        self.assertAlmostEqual(df1["y"].iloc[0], math.log(50.0))
        self.assertAlmostEqual(df1["y"].iloc[1], math.log(60.0))

    def test_date_column_is_timezone_free(self):
        self._add_lot(self.koppe_id, price=100.0, lot_date="2020-05-05")
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertIsNone(df["date"].dt.tz)

    def test_provider_name_not_id(self):
        self._add_lot(self.langtons_id, price=100.0)
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(df["provider"].iloc[0], "langtons")

    def test_house_offset_is_subtracted_from_y(self):
        # D8 (User decision, 2026-11-11): y is house-adjusted --
        # ln(price) minus the persisted provider_effects.offset for
        # that lot's own provider.
        self._add_lot(self.langtons_id, price=100.0)
        provider_id = self.conn.execute(
            "SELECT id FROM providers WHERE name='langtons'").fetchone()[0]
        self.conn.execute(
            "INSERT INTO provider_effects(provider_id, offset, n_obs)"
            " VALUES (?, 0.5, 10)", (provider_id,))
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertAlmostEqual(df["y"].iloc[0], math.log(100.0) - 0.5)

    def test_provider_with_no_persisted_offset_is_unadjusted(self):
        # No provider_effects row at all for this provider (e.g. too
        # few observations for fit_provider_effects to include it) --
        # COALESCE to 0, not a crash or a NULL y.
        self._add_lot(self.langtons_id, price=100.0)
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertAlmostEqual(df["y"].iloc[0], math.log(100.0))

    def test_house_offset_column_lets_the_raw_log_price_be_recovered(self):
        # G1 fix (Copilot review, Finding 1): forecast/eval.py needs to
        # undo this offset per rolling origin -- only possible if
        # y + house_offset recovers ln(price_per_bottle_eur) exactly.
        self._add_lot(self.langtons_id, price=100.0)
        provider_id = self.conn.execute(
            "SELECT id FROM providers WHERE name='langtons'").fetchone()[0]
        self.conn.execute(
            "INSERT INTO provider_effects(provider_id, offset, n_obs)"
            " VALUES (?, 0.5, 10)", (provider_id,))
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertAlmostEqual(df["house_offset"].iloc[0], 0.5)
        self.assertAlmostEqual(
            df["y"].iloc[0] + df["house_offset"].iloc[0], math.log(100.0))

    def test_different_wine_ref_id_is_a_different_series(self):
        self._add_lot(self.koppe_id, wine_ref_id=1, price=100.0)
        self._add_lot(self.koppe_id, wine_ref_id=2, price=9999.0)
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df["y"].iloc[0], math.log(100.0))

    def test_different_vintage_is_a_different_series(self):
        self._add_lot(self.koppe_id, vintage_final=2015, price=100.0)
        self._add_lot(self.koppe_id, vintage_final=2016, price=9999.0)
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df["y"].iloc[0], math.log(100.0))

    def test_different_size_class_is_a_different_series(self):
        self._add_lot(self.koppe_id, bottle_size_dl=7.5, price=100.0)
        self._add_lot(self.koppe_id, bottle_size_dl=15.0, price=9999.0)
        df = fdata.load_series(self.conn, 1, 2015, 7.5)
        self.assertEqual(len(df), 1)
        self.assertAlmostEqual(df["y"].iloc[0], math.log(100.0))


class LoadAllSeriesTest(unittest.TestCase):
    """1.5: bulk loader for the evaluator. Deliberately NOT built on
    ``df.groupby()`` (measured 40 minutes on the live ~971k-row /
    ~120k-series DB; a boundary scan over the SQL-sorted rows does the
    same split in ~34s) -- these tests check the boundary scan finds
    exactly the same split a groupby would, not just "doesn't crash"."""

    RECENT = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)
        self.koppe_id = self.builder.add_auction(
            "koppe", "1", "x", None, "EUR", "HAMMER")
        self._lot_no = 0

    def tearDown(self):
        self.conn.close()

    def _add_lot(self, wine_ref_id, vintage_final, bottle_size_dl, price,
                 lot_date=None):
        lot_date = lot_date or self.RECENT
        self._lot_no += 1
        lot_id = self.builder.add_lot(self.koppe_id, {
            "lot_no": str(self._lot_no), "wine": "test-wine",
            "wine_ref_id": wine_ref_id, "bottle_size_dl": bottle_size_dl,
            "quantity": 1, "lot_date": lot_date, "sold": 1,
            "hammer_price": price})
        self.conn.execute(
            "UPDATE lots SET lot_kind='SINGLE', vintage_status='STRUCTURED',"
            " vintage_final=?, price_per_bottle_eur=? WHERE id=?",
            (vintage_final, price, lot_id))

    def test_empty_db_returns_empty_list(self):
        self.assertEqual(fdata.load_all_series(self.conn), [])

    def test_splits_into_the_right_number_of_series_with_right_sizes(self):
        self._add_lot(1, 2015, 7.5, 100.0)
        self._add_lot(1, 2015, 7.5, 110.0)  # same series, 2nd row
        self._add_lot(1, 2016, 7.5, 200.0)  # different vintage
        self._add_lot(2, 2015, 7.5, 300.0)  # different wine_ref_id
        out = fdata.load_all_series(self.conn)
        sizes = {key: len(df) for key, df in out}
        self.assertEqual(
            sizes, {(1, 2015, 7.5): 2, (1, 2016, 7.5): 1, (2, 2015, 7.5): 1})

    def test_house_offset_is_subtracted_from_y(self):
        # D8 (User decision, 2026-11-11): same house-adjustment as
        # load_series, applied here too.
        self._add_lot(1, 2015, 7.5, 100.0)
        provider_id = self.conn.execute(
            "SELECT id FROM providers WHERE name='koppe'").fetchone()[0]
        self.conn.execute(
            "INSERT INTO provider_effects(provider_id, offset, n_obs)"
            " VALUES (?, 0.5, 10)", (provider_id,))
        out = dict(fdata.load_all_series(self.conn))
        self.assertAlmostEqual(
            out[(1, 2015, 7.5)]["y"].iloc[0], math.log(100.0) - 0.5)

    def test_matches_load_series_for_the_same_key(self):
        self._add_lot(1, 2015, 7.5, 100.0,
                      lot_date=(datetime.date.today()
                               - datetime.timedelta(days=100)).isoformat())
        self._add_lot(1, 2015, 7.5, 120.0,
                      lot_date=(datetime.date.today()
                               - datetime.timedelta(days=10)).isoformat())
        self._add_lot(9, 2020, 15.0, 999.0)
        out = dict(fdata.load_all_series(self.conn))
        bulk = out[(1, 2015, 7.5)].reset_index(drop=True)
        single = fdata.load_series(self.conn, 1, 2015, 7.5)
        pd.testing.assert_frame_equal(bulk, single)

    def test_sorted_by_key_then_date(self):
        self._add_lot(2, 2015, 7.5, 100.0)
        self._add_lot(1, 2016, 7.5, 100.0)
        self._add_lot(1, 2015, 7.5, 100.0)
        out = fdata.load_all_series(self.conn)
        self.assertEqual(
            [key for key, _ in out],
            [(1, 2015, 7.5), (1, 2016, 7.5), (2, 2015, 7.5)])


if __name__ == "__main__":
    unittest.main()
