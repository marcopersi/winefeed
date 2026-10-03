import os
import tempfile
import unittest
from unittest import mock

from ingest.models import AuctionRef, FetchResult
from ingest.registry import get_last_run, load_manifest
from ingest.runner import run_provider


class FakeFetcher:
    provider = "steinfels"

    def discover(self, session):
        return [
            AuctionRef("steinfels", "627", url="u627"),
            AuctionRef("steinfels", "628", url="u628"),
        ]

    def fetch(self, session, ref):
        return FetchResult(provider=ref.provider, auction_id=ref.auction_id,
                           data={"auction_id": ref.auction_id})


class TestRunner(unittest.TestCase):
    def test_run_fetches_only_new_and_marks_last_run(self):
        with tempfile.TemporaryDirectory() as d:
            manifest_path = os.path.join(d, "manifest.json")
            archive_dir = os.path.join(d, "archive")
            with mock.patch("ingest.runner.get", return_value=FakeFetcher()):
                # first run: both auctions fetched
                fetched = run_provider("steinfels", None, manifest_path,
                                       archive_dir)
                self.assertEqual(fetched, 2)
                self.assertIsNotNone(
                    get_last_run(load_manifest(manifest_path), "steinfels"))
                # second run: nothing new
                fetched = run_provider("steinfels", None, manifest_path,
                                       archive_dir)
                self.assertEqual(fetched, 0)
            files = os.listdir(archive_dir)
            self.assertEqual(sorted(files),
                             ["steinfels__627.json", "steinfels__628.json"])


if __name__ == "__main__":
    unittest.main()
