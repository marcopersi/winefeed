import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wine_resolution.normalize import normalize  # noqa: E402
from wine_resolution import resolver as r  # noqa: E402


def obs(raw, producer=None, region=None):
    return {
        "alias_raw": raw,
        "alias_key": normalize(raw),
        "producer_raw": producer,
        "producer_key": normalize(producer),
        "region_raw": region,
        "region_key": normalize(region),
        "evidence_count": 1,
    }


class TestResolver(unittest.TestCase):
    def test_diacritics_resolve(self):
        res = r.resolve_group([obs("Chateau Margaux"), obs("Château Margaux")])
        self.assertEqual(res["status"], r.STATUS_RESOLVED)
        self.assertIn("Margaux", res["canonical_name"])

    def test_petrus_resolve(self):
        res = r.resolve_group([obs("Petrus"), obs("Pétrus")])
        self.assertEqual(res["status"], r.STATUS_RESOLVED)
        self.assertEqual(res["canonical_name"], "Pétrus")

    def test_conflicting_producer(self):
        res = r.resolve_group([
            obs("Château X", producer="A"),
            obs("Château X", producer="B"),
        ])
        self.assertEqual(res["status"], r.STATUS_AMBIGUOUS)
        self.assertEqual(res["reason"], "conflicting-producer")

    def test_conflicting_region(self):
        res = r.resolve_group([
            obs("Château X", region="Pauillac"),
            obs("Château X", region="Saint-Julien"),
        ])
        self.assertEqual(res["status"], r.STATUS_AMBIGUOUS)
        self.assertEqual(res["reason"], "conflicting-region")

    def test_stable_key_deterministic(self):
        k1 = r.stable_key("chateau margaux", "chateau margaux", "")
        k2 = r.stable_key("chateau margaux", "chateau margaux", "")
        self.assertEqual(k1, k2)

    def test_override_merges_chateau_petrus(self):
        # The resolver itself does not strip "Chateau"; the override provides
        # the merge at the orchestration layer. Here we assert that the raw
        # names produce *different* keys (so the override is required).
        self.assertNotEqual(normalize("Petrus"), normalize("Château Petrus"))


if __name__ == "__main__":
    unittest.main()
