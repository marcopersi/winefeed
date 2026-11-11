"""D8/D9 (price-prediction-plan.md): build_db._persist_provider_effects
-- persists forecast.models.fit_provider_effects' house offsets into the
provider_effects table so Stufe 1/2's models load the same house-adjusted
y (forecast/data.py).
"""
# pylint: disable=protected-access
import datetime
import math
import sqlite3
import unittest

import build_db


class PersistProviderEffectsTest(unittest.TestCase):
    RECENT = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()

    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.executescript(build_db.SCHEMA)
        self.builder = build_db.Builder(self.conn)
        self._lot_no = 0

    def tearDown(self):
        self.conn.close()

    def _add_row(self, auction_id, wine_ref_id, vintage, price):
        self._lot_no += 1
        lot_id = self.builder.add_lot(auction_id, {
            "lot_no": str(self._lot_no), "wine": "test-wine",
            "wine_ref_id": wine_ref_id, "bottle_size_dl": 7.5,
            "quantity": 1, "lot_date": self.RECENT, "sold": 1,
            "hammer_price": price})
        self.conn.execute(
            "UPDATE lots SET lot_kind='SINGLE', vintage_status='STRUCTURED',"
            " vintage_final=?, price_per_bottle_eur=? WHERE id=?",
            (vintage, price, lot_id))

    def _populate_two_providers(self):
        koppe_id = self.builder.add_auction(
            "koppe", "1", "x", None, "EUR", "HAMMER")
        langtons_id = self.builder.add_auction(
            "langtons", "1", "x", None, "EUR", "HAMMER")
        # langtons priced systematically higher -- a real offset to
        # recover, same balanced-design idea as
        # test_forecast_models.FitProviderEffectsTest.
        for wine_ref_id, base in ((1, 100.0), (2, 50.0)):
            self._add_row(koppe_id, wine_ref_id, 2015, base)
            self._add_row(langtons_id, wine_ref_id, 2015, base * math.exp(0.3))

    def test_persists_offsets_keyed_by_provider_id(self):
        self._populate_two_providers()
        build_db._persist_provider_effects(self.conn)
        rows = dict(self.conn.execute(
            "SELECT p.name, pe.offset FROM provider_effects pe"
            " JOIN providers p ON p.id = pe.provider_id"))
        self.assertEqual(set(rows), {"koppe", "langtons"})
        # Centered: observation-weighted mean of offsets is 0 (balanced
        # design here, so a plain mean of the two).
        self.assertAlmostEqual(
            sum(rows.values()) / len(rows), 0.0, places=6)
        self.assertAlmostEqual(
            rows["langtons"] - rows["koppe"], 0.3, places=6)

    def test_n_obs_is_persisted_too(self):
        self._populate_two_providers()
        build_db._persist_provider_effects(self.conn)
        n_obs = dict(self.conn.execute(
            "SELECT p.name, pe.n_obs FROM provider_effects pe"
            " JOIN providers p ON p.id = pe.provider_id"))
        self.assertEqual(n_obs, {"koppe": 2, "langtons": 2})

    def test_empty_forecast_input_clears_the_table_without_crashing(self):
        build_db._persist_provider_effects(self.conn)
        rows = self.conn.execute("SELECT * FROM provider_effects").fetchall()
        self.assertEqual(rows, [])

    def test_rerun_replaces_rather_than_accumulates(self):
        self._populate_two_providers()
        build_db._persist_provider_effects(self.conn)
        build_db._persist_provider_effects(self.conn)
        n = self.conn.execute(
            "SELECT COUNT(*) FROM provider_effects").fetchone()[0]
        self.assertEqual(n, 2)


if __name__ == "__main__":
    unittest.main()
