"""Tests for the producer + wine reference-list matching (§4.2/4.3)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution.producer_match import ProducerMatcher


class TestProducerMatcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matcher = ProducerMatcher()

    def test_match_producer_abbreviation(self):
        self.assertEqual(self.matcher.match_producer("J.F Coche-Dury"),
                         "Coche-Dury")

    def test_match_producer_full_name(self):
        self.assertEqual(self.matcher.match_producer("Weingut Bernhard Huber"),
                         "Weingut Bernhard Huber")

    def test_match_wine_synonym(self):
        self.assertEqual(
            self.matcher.match_wine("Coche-Dury", "Meursault Les Perrières"),
            "Meursault Perrières")

    def test_match_wine_schlossberg(self):
        self.assertEqual(
            self.matcher.match_wine("Weingut Bernhard Huber",
                                   "R Schlossberg GG"),
            "Hecklinger Schlossberg R Spätburgunder GG")

    def test_no_producer(self):
        self.assertIsNone(self.matcher.match_producer("Unbekannter Wein 1990"))


if __name__ == "__main__":
    unittest.main()
