import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution.normalize import normalize, is_valid_name  # noqa: E402


class TestNormalize(unittest.TestCase):
    def test_diacritics(self):
        self.assertEqual(normalize("Chateau Margaux"),
                         normalize("Château Margaux"))

    def test_petrus(self):
        self.assertEqual(normalize("Petrus"), normalize("Pétrus"))

    def test_apostrophe(self):
        self.assertEqual(normalize("L'Eglise-Clinet"),
                         normalize("L Eglise Clinet"))

    def test_double_dash(self):
        self.assertEqual(normalize("PENFOLDS Bin 95--Grange"),
                         normalize("PENFOLDS Bin 95 Grange"))

    def test_case_and_whitespace(self):
        self.assertEqual(normalize("  CHATEAU   MARGAUX "),
                         normalize("chateau margaux"))

    def test_none(self):
        self.assertEqual(normalize(None), "")

    def test_valid(self):
        self.assertTrue(is_valid_name("Château Margaux"))

    def test_invalid_number_only(self):
        self.assertFalse(is_valid_name("1"))
        self.assertFalse(is_valid_name("2"))

    def test_invalid_noise(self):
        self.assertFalse(is_valid_name("1 ^,,^^,,^"))

    def test_invalid_empty(self):
        self.assertFalse(is_valid_name(""))


if __name__ == "__main__":
    unittest.main()
