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


class TestMatchProducerAndWine(unittest.TestCase):
    """Confirmed real cases: a classification/state/provenance code sitting
    in the raw ``producer`` field (VdT, OHK, SBE, AGE, pure parse junk) is
    not a producer at all and must be treated like a missing producer,
    not carried through as a dead-end value -- see build_wines.py's
    _JUNK_PRODUCER_CODES for the confirmed evidence per code."""

    @classmethod
    def setUpClass(cls):
        import build_wines
        cls.build_wines = build_wines
        cls.matcher = ProducerMatcher()

    def test_vdt_code_rejected_falls_back_to_name_extraction(self):
        wine, producer = self.build_wines._match_producer_and_wine(
            self.matcher, "Weingut Bernhard Huber Spätburgunder", "VdT")
        self.assertEqual(producer, "Weingut Bernhard Huber")

    def test_junk_parse_artifact_rejected(self):
        wine, producer = self.build_wines._match_producer_and_wine(
            self.matcher, "Unbekannter Wein 1990", "0")
        self.assertIsNone(producer)

    def test_real_producer_is_not_rejected(self):
        wine, producer = self.build_wines._match_producer_and_wine(
            self.matcher, "Meursault Les Perrières", "Coche-Dury")
        self.assertEqual(producer, "Coche-Dury")


if __name__ == "__main__":
    unittest.main()
