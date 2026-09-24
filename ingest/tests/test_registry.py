import os
import tempfile
import unittest

from ingest.models import AuctionRef
from ingest.registry import dedup, load_manifest, mark_fetched, save_manifest


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


if __name__ == "__main__":
    unittest.main()
