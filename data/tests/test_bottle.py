import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution import bottle as b  # noqa: E402


class TestBottleFormat(unittest.TestCase):
    def test_bt(self):
        self.assertEqual(b.parse_bottle_format("La Tâche 2009 (6 BT)"),
                         (6, 7.5))

    def test_mag(self):
        self.assertEqual(b.parse_bottle_format("Morey St. Denis 1996 (6 MAG)"),
                         (6, 15.0))

    def test_dm(self):
        self.assertEqual(b.parse_bottle_format("Château X (2 DM)"), (2, 30.0))

    def test_hb(self):
        self.assertEqual(b.parse_bottle_format("Château X (6 HB)"),
                         (6, 3.75))

    def test_imperiale(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 IMP)"), (1, 60.0))

    def test_methuselah(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 METH)"), (1, 60.0))

    def test_salmanazar(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 SALR)"), (1, 90.0))

    def test_balthazar(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 BALR)"), (1, 120.0))

    def test_nebuchadnezzar(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 NEBR)"), (1, 150.0))

    def test_melchior(self):
        self.assertEqual(b.parse_bottle_format("Krug (1 MELR)"), (1, 180.0))

    def test_liter(self):
        self.assertEqual(b.parse_bottle_format("Petrus 2014 (3 Ltr)"),
                         (1, 30.0))

    def test_no_hint(self):
        self.assertEqual(b.parse_bottle_format("Château Margaux"),
                         (None, None))

    def test_label_state_not_parsed(self):
        # E.T.H / E.L.A are label-state codes, not bottle formats.
        self.assertEqual(
            b.parse_bottle_format("Pomerol (e.t.h dont 1 e.t.a)"),
            (None, None))

    def test_takes_first_recognised(self):
        # "1 BT and Petrus 1985 1 BT" style is rare; ensure a real format wins.
        self.assertEqual(b.parse_bottle_format("Château X (2 BT) (1 MAG)"),
                         (2, 7.5))


class TestStripBottleFormat(unittest.TestCase):
    """Confirmed real case: "Sassicaia" vs. "Sassicaia (2 BT)" vs.
    "Sassicaia (3 BT)" fragment into separate wines rows for the same
    real wine because the bottle-format hint was never removed from the
    name used to build alias_key."""

    def test_strips_trailing_bracket(self):
        self.assertEqual(b.strip_bottle_format("Sassicaia (2 BT)"),
                          "Sassicaia")

    def test_strips_mid_name_bracket(self):
        self.assertEqual(
            b.strip_bottle_format("Sassicaia (6 BT) 1990"), "Sassicaia 1990")

    def test_strips_plain_form(self):
        self.assertEqual(b.strip_bottle_format("Krug 1 Magnum"), "Krug")

    def test_strips_liter_form(self):
        self.assertEqual(b.strip_bottle_format("Petrus 2014 3 Ltr"),
                          "Petrus 2014")

    def test_no_match_is_unchanged(self):
        self.assertEqual(b.strip_bottle_format("Château Margaux"),
                          "Château Margaux")

    def test_label_state_code_not_stripped(self):
        self.assertEqual(
            b.strip_bottle_format("Pomerol (e.t.h dont 1 e.t.a)"),
            "Pomerol (e.t.h dont 1 e.t.a)")

    def test_empty_is_unchanged(self):
        self.assertEqual(b.strip_bottle_format(""), "")
        self.assertIsNone(b.strip_bottle_format(None))


if __name__ == "__main__":
    unittest.main()
