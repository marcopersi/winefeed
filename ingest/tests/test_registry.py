import os
import tempfile
import unittest

from ingest.models import AuctionRef
from ingest.registry import (dedup, get_last_run, load_manifest, mark_fetched,
                             save_manifest, sequence_gaps, set_last_run)


class TestRegistry(unittest.TestCase):
    def test_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "manifest.json")
            m = {"steinfels": {"627": {"url": "u", "etag": "", "fetched_at": ""}}}
            save_manifest(path, m)
            self.assertEqual(load_manifest(path), m)

    def test_dedup_filters_seen(self):
        manifest = {"steinfels": {"627": {}}}
        refs = [AuctionRef("steinfels", "627"),
                AuctionRef("steinfels", "628"),
                AuctionRef("weinboerse", "627")]
        new = dedup(refs, manifest, "steinfels")
        self.assertEqual([r.auction_id for r in new], ["628"])

    def test_mark_fetched(self):
        manifest = {}
        mark_fetched(manifest, AuctionRef("steinfels", "627", url="u"))
        self.assertIn("627", manifest["steinfels"])
        self.assertEqual(manifest["steinfels"]["627"]["url"], "u")

    def test_last_run_roundtrip(self):
        manifest = {}
        self.assertIsNone(get_last_run(manifest, "steinfels"))
        set_last_run(manifest, "steinfels", "2026-10-03T00:00:00+00:00")
        self.assertEqual(get_last_run(manifest, "steinfels"),
                         "2026-10-03T00:00:00+00:00")
        # last-run marker must not break dedup
        refs = [AuctionRef("steinfels", "627"),
                AuctionRef("steinfels", "628")]
        self.assertEqual([r.auction_id for r in dedup(refs, manifest, "steinfels")],
                         ["627", "628"])


class TestSequenceGaps(unittest.TestCase):
    def test_finds_missing_ids_in_range(self):
        """Confirmed real finding: weinauktionator ids 23 and 27 were never
        fetched, with no file anywhere in the archive and a 404 on the
        direct download URL -- a gap like this needs to surface the month
        it happens, not an unknown number of months later."""
        manifest = {"weinauktionator": {
            str(n): {} for n in [20, 21, 22, 24, 25, 26, 28, 29]}}
        self.assertEqual(sequence_gaps(manifest, "weinauktionator"),
                         [23, 27])

    def test_no_gap_is_empty(self):
        manifest = {"steinfels": {str(n): {} for n in [34, 35, 36]}}
        self.assertEqual(sequence_gaps(manifest, "steinfels"), [])

    def test_ignores_last_run_marker(self):
        manifest = {"steinfels": {
            "34": {}, "35": {},
            "__last_run_at__": "2026-11-25T00:00:00+00:00"}}
        self.assertEqual(sequence_gaps(manifest, "steinfels"), [])

    def test_non_numeric_ids_are_not_a_false_positive(self):
        manifest = {"koppe": {"2026-01-05": {}, "2026-02-03": {}}}
        self.assertEqual(sequence_gaps(manifest, "koppe"), [])

    def test_single_id_is_not_enough_to_judge(self):
        manifest = {"weinauktionator": {"34": {}}}
        self.assertEqual(sequence_gaps(manifest, "weinauktionator"), [])

    def test_unknown_provider_is_empty(self):
        self.assertEqual(sequence_gaps({}, "weinauktionator"), [])

    def test_absurd_span_is_treated_as_corrupt_not_a_gap(self):
        """Review finding (2026-11-25): one bad numeric key (a manual-edit
        typo, a parsing glitch) would otherwise size the range/set off
        that single outlier with no bound at all."""
        manifest = {"steinfels": {"34": {}, "99999999": {}}}
        self.assertEqual(sequence_gaps(manifest, "steinfels"), [])


if __name__ == "__main__":
    unittest.main()
