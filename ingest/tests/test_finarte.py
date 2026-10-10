import unittest

from ingest.fetchers.finarte import FinarteFetcher

LIST_HTML = (
    '<a href="/auction/fine-wines-milan-2026-09-16">x</a>'
    '<a href="/auction/fine-spirits-milan-2026-03-18">y</a>'
    '<a href="/auction/fine-wines-milan-2026-09-16">dup</a>')

LOT_PAGE = (
    '<script id="__DATI_LOTTI__" type="application/json">'
    '[{"numero_lotto":"1","stringa_filtro_autore_lotto":"Gaja (1 BT)",'
    '"stringa_categoria_lotto":"Barbaresco","anno":"1981",'
    '"prezzo_aggiudicazione":221.4,"valore_min":"180","valore_max":"220",'
    '"opera_venduta":"True","regime_vendita":"RF15"}]'
    '</script>')


class FakeResponse:
    def __init__(self, text):
        self.text = text
        self.content = b""

    def raise_for_status(self):
        return None


class FakeSession:
    def __init__(self, pages):
        self._pages = pages

    def get(self, url):
        for key, text in self._pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")

    def post(self, *args, **kwargs):  # pylint: disable=unused-argument
        return FakeResponse('{"finarte":{"success":true}}')


class TestFinarte(unittest.TestCase):
    def test_auth_success(self):
        f = FinarteFetcher()
        ok = f.auth(FakeSession({}), {"FINARTE_USER": "x",
                                      "FINARTE_PWD": "y"})
        self.assertTrue(ok)

    def test_discover_dedupes_slugs(self):
        f = FinarteFetcher()
        refs = f.discover(FakeSession({"past-auctions": LIST_HTML}))
        self.assertEqual([r.auction_id for r in refs], ["16", "18"])

    def test_fetch_extracts_lots(self):
        f = FinarteFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("finarte", "16",
                         url="https://www.finarte.it/auction/fine-wines-16")
        result = f.fetch(FakeSession({"auction/fine-wines-16": LOT_PAGE}), ref)
        self.assertEqual(result.data["auction"]["slug"], "fine-wines-16")
        self.assertEqual(len(result.data["lots"]), 1)
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_nr"], "1")
        self.assertEqual(lot["name"], "Gaja (1 BT)")
        self.assertEqual(lot["region"], "Barbaresco")
        self.assertEqual(lot["vintage"], "1981")
        self.assertEqual(lot["hammer_price"], 221.4)
        self.assertEqual(lot["estimate_min"], "180")
        self.assertEqual(lot["sold"], 1)


if __name__ == "__main__":
    unittest.main()
