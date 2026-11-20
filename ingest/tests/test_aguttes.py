# pylint: disable=protected-access
import json
import unittest

from ingest.fetchers.aguttes import (
    WINE_DEPARTMENT_UUID, AguttesFetcher, MalformedResponse,
    ReconciliationMismatch, _premium_rate_ht,
)
from ingest.models import AuctionRef

OTHER_DEPARTMENT_UUID = "035b3a7f-5042-4533-9bb8-bc0d7ab85eda"


def _next_data_html(payload):
    return (
        '<script id="__NEXT_DATA__" type="application/json">'
        + json.dumps(payload) + "</script>")


def _listing_html(results, page=1, total_pages=1, count=None):
    return _next_data_html({"props": {"pageProps": {"dehydratedState": {
        "queries": [{"state": {"data": {
            "count": count if count is not None else len(results),
            "limit": 20, "page": page, "total_pages": total_pages,
            "results": results,
        }}}],
    }}}})


def _sale_entry(uuid, department_uuid=WINE_DEPARTMENT_UUID,
                title="Grands Vins & Spiritueux", start_date="2026-11-04T09:00:00.000Z"):
    return {
        "uuid": uuid, "department_uuid": department_uuid,
        "title": {"fr": title, "en": title},
        "dates": [{"start_date": start_date, "start_lot": "1", "end_lot": None}],
    }


def _catalogue_html(auction, lots, page=1, limit=24, count=None):
    return _next_data_html({"props": {"pageProps": {
        "auction": auction,
        "auctionLots": {
            "count": count if count is not None else len(lots),
            "limit": limit, "page": page, "results": lots,
        },
    }}})


def _auction_meta(sale_no="V26VIN08", title="Grands Vins & Spiritueux",
                  start_date="2026-11-04T09:00:00.000Z", tax_rate="20.0000",
                  premiums=None):
    return {
        "sale_no": sale_no, "title": {"fr": title, "en": title},
        "dates": [{"start_date": start_date, "start_lot": "1", "end_lot": None}],
        "tax_rate": tax_rate,
        "premiums": premiums if premiums is not None else [
            {"percent": 21, "amount_over": 0},
        ],
    }


def _lot(lot_no, description, status="sold", hammer_price="280.00",
        low="150.00", high="170.00"):
    return {
        "lot_no": lot_no, "status": status, "hammer_price": hammer_price,
        "low": low, "high": high,
        "dynamic_fields": {
            "fr": {"title": "<p>Margaux</p>",
                  "description": f"<p>{description}</p>"},
        },
    }


class FakeSession:
    def __init__(self, listing_pages=None, catalogue_pages=None):
        self._listing = listing_pages or {}
        self._catalogue = catalogue_pages or {}
        self.requests = []

    def get(self, url, params=None):
        page = (params or {}).get("page", 1)
        self.requests.append((url, page))
        if url.endswith("/ventes/ventes-passees"):
            html = self._listing.get(page, "")
        else:
            html = self._catalogue.get((url, page), "")
        return _FakeResponse(html)


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class DiscoverTests(unittest.TestCase):
    def test_keeps_only_the_wine_department_and_builds_refs(self):
        html = _listing_html([
            _sale_entry("wine-1", title="Grands Vins & Spiritueux"),
            _sale_entry("other-1", department_uuid=OTHER_DEPARTMENT_UUID,
                       title="Bijoux & Montres"),
        ])
        session = FakeSession(listing_pages={1: html})
        refs = AguttesFetcher().discover(session)
        self.assertEqual(len(refs), 1)
        ref = refs[0]
        self.assertEqual(ref.auction_id, "wine-1")
        self.assertEqual(ref.url, "https://www.aguttes.com/catalogue/wine-1")
        self.assertEqual(ref.title, "Grands Vins & Spiritueux")
        self.assertEqual(ref.date, "2026-11-04")

    def test_pages_through_the_listing_until_total_pages(self):
        page1 = _listing_html([_sale_entry("wine-1")], page=1, total_pages=2)
        page2 = _listing_html([_sale_entry("wine-2")], page=2, total_pages=2)
        session = FakeSession(listing_pages={1: page1, 2: page2})
        refs = AguttesFetcher().discover(session)
        self.assertEqual({r.auction_id for r in refs}, {"wine-1", "wine-2"})

    def test_missing_next_data_raises(self):
        session = FakeSession(listing_pages={1: "<html>no next data</html>"})
        with self.assertRaises(MalformedResponse):
            AguttesFetcher().discover(session)


class FetchTests(unittest.TestCase):
    def _ref(self, uuid="a04bdf93"):
        return AuctionRef(provider="aguttes", auction_id=uuid,
                          url=f"https://www.aguttes.com/catalogue/{uuid}",
                          title="Grands Vins & Spiritueux", date="2026-11-04")

    def test_parses_auction_and_sold_lot_with_premium(self):
        auction = _auction_meta()
        lots = [_lot("1", "1 B CHÂTEAU PALMER - 1979 - GCC3 Margaux")]
        html = _catalogue_html(auction, lots)
        session = FakeSession(catalogue_pages={
            (self._ref().url, 1): html})
        result = AguttesFetcher().fetch(session, self._ref())

        self.assertEqual(result.data["auction"], {
            "id": "a04bdf93", "name": "Grands Vins & Spiritueux",
            "date": "2026-11-04", "currency": "EUR", "vat_rate": 0.2,
            "sale_no": "V26VIN08", "price_basis": "HAMMER",
        })
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_no"], "1")
        self.assertEqual(lot["wine"], "1 B CHÂTEAU PALMER - 1979 - GCC3 Margaux")
        self.assertEqual(lot["vintage"], "1979")
        self.assertEqual(lot["quantity"], 1)
        self.assertEqual(lot["estimate_low"], 150.0)
        self.assertEqual(lot["estimate_high"], 170.0)
        self.assertEqual(lot["hammer_price"], 280.0)
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["premium_rate"], 0.21)

    def test_unsold_lot_has_no_hammer_price_or_premium(self):
        auction = _auction_meta()
        lots = [_lot("2", "2 B CHÂTEAU TALBOT - 1990 - GCC4 Saint-Julien",
                     status="unsold", hammer_price=None)]
        html = _catalogue_html(auction, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["hammer_price"])
        self.assertIsNone(lot["premium_rate"])

    def test_same_year_mentioned_twice_is_not_ambiguous(self):
        auction = _auction_meta()
        lots = [_lot("4", "1 B WINE A - 1990 - Region "
                           "1 B WINE B - 1990 - Region")]
        html = _catalogue_html(auction, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        self.assertEqual(result.data["lots"][0]["vintage"], "1990")

    def test_ambiguous_multi_vintage_text_leaves_vintage_null(self):
        auction = _auction_meta()
        lots = [_lot("3", "5 B AUXEY-DURESSES - 2018 - Domaine Roulot "
                           "1 B AUXEY-DURESSES - 2017 - Domaine Roulot")]
        html = _catalogue_html(auction, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        self.assertIsNone(result.data["lots"][0]["vintage"])

    def test_tiered_premium_steps_down_above_threshold(self):
        auction = _auction_meta(premiums=[
            {"percent": 25, "amount_over": 0},
            {"percent": 20, "amount_over": 10000},
        ])
        lots = [
            _lot("1", "1 B WINE A", hammer_price="5000.00"),
            _lot("2", "1 B WINE B", hammer_price="20000.00"),
        ]
        html = _catalogue_html(auction, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        self.assertEqual(result.data["lots"][0]["premium_rate"], 0.25)
        self.assertEqual(result.data["lots"][1]["premium_rate"], 0.20)

    def test_pages_through_a_multi_page_catalogue(self):
        auction = _auction_meta()
        page1_lots = [_lot(str(i), f"1 B WINE {i}") for i in range(1, 25)]
        page2_lots = [_lot("25", "1 B WINE 25")]
        ref = self._ref()
        html1 = _catalogue_html(auction, page1_lots, page=1, limit=24, count=25)
        html2 = _catalogue_html(auction, page2_lots, page=2, limit=24, count=25)
        session = FakeSession(catalogue_pages={
            (ref.url, 1): html1, (ref.url, 2): html2})
        result = AguttesFetcher().fetch(session, ref)
        self.assertEqual(len(result.data["lots"]), 25)

    def test_reconciliation_mismatch_raises(self):
        auction = _auction_meta()
        # advertised count=5, but no more pages ever yield the remaining
        # lots -- the loop stops once `results` is empty, which must be
        # treated as a real problem, not silently archived short.
        html1 = _catalogue_html(auction, [_lot("1", "1 B WINE")],
                                page=1, limit=24, count=5)
        html2 = _catalogue_html(auction, [], page=2, limit=24, count=5)
        ref = self._ref()
        session = FakeSession(catalogue_pages={
            (ref.url, 1): html1, (ref.url, 2): html2})
        with self.assertRaises(ReconciliationMismatch):
            AguttesFetcher().fetch(session, ref)

    def test_missing_next_data_raises(self):
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): "<html></html>"})
        with self.assertRaises(MalformedResponse):
            AguttesFetcher().fetch(session, ref)

    def test_sold_lot_below_every_premium_tier_raises(self):
        # Schedule only covers hammer prices >= 10000; a sold lot below
        # that must fail loud, not silently archive without a price.
        auction = _auction_meta(premiums=[
            {"percent": 20, "amount_over": 10000}])
        lots = [_lot("1", "1 B WINE", hammer_price="50.00")]
        html = _catalogue_html(auction, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        with self.assertRaises(RuntimeError):
            AguttesFetcher().fetch(session, ref)

    def test_missing_auctionlots_count_raises(self):
        ref = self._ref()
        html = _next_data_html({"props": {"pageProps": {
            "auction": _auction_meta(), "auctionLots": {"results": []},
        }}})
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        with self.assertRaises(MalformedResponse):
            AguttesFetcher().fetch(session, ref)


def _drouot_gateway_html(vente, lots):
    return _next_data_html({"props": {"pageProps": {
        "auction": None, "auctionLots": None,
        "drouotVente": vente, "drouotLots": lots,
    }}})


def _drouot_vente(sale_id=170340, title_fr="Grands vins & Spiritueux",
                  date="2026-05-14"):
    return {"sale_id": sale_id, "title_fr": title_fr,
           "title_en": "Fine Wines & Spirits", "date": date,
           "statut": "CLOSED"}


def _drouot_lot(number, title_fr, adjudication_price_with_fees="0.00",
                low_estimate="100.00", high_estimate="120.00",
                number_extension=None):
    return {
        "number": number, "number_extension": number_extension,
        "title_fr": title_fr, "title_en": title_fr,
        "low_estimate": low_estimate, "high_estimate": high_estimate,
        "adjudication_price_with_fees": adjudication_price_with_fees,
        "adj_not_provided": "false",
    }


class DrouotGatewayFetchTests(unittest.TestCase):
    def _ref(self, uuid="fc8a6eb5"):
        return AuctionRef(provider="aguttes", auction_id=uuid,
                          url=f"https://www.aguttes.com/catalogue/{uuid}",
                          title="Grands vins & Spiritueux", date="2026-05-14")

    def test_sold_lot_uses_fee_inclusive_price_directly(self):
        vente = _drouot_vente()
        lots = [_drouot_lot(1, "3 B CHABLIS LA FOREST - 2005 - Domaine X",
                            adjudication_price_with_fees="260.00")]
        html = _drouot_gateway_html(vente, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)

        self.assertEqual(result.data["auction"], {
            "id": "fc8a6eb5", "name": "Grands vins & Spiritueux",
            "date": "2026-05-14", "currency": "EUR", "sale_no": "170340",
            "price_basis": "HAMMER_PLUS_BUYERS_PREMIUM",
        })
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_no"], "1")
        self.assertEqual(lot["vintage"], "2005")
        self.assertEqual(lot["quantity"], 3)
        self.assertEqual(lot["estimate_low"], 100.0)
        self.assertEqual(lot["estimate_high"], 120.0)
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["realised_price"], 260.0)

    def test_zero_price_means_unsold_not_a_real_zero_price(self):
        vente = _drouot_vente()
        lots = [_drouot_lot(2, "1 B SOME WINE - 2010 - Domaine Y",
                            adjudication_price_with_fees="0.00")]
        html = _drouot_gateway_html(vente, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["realised_price"])

    def test_number_extension_is_appended_to_lot_no(self):
        vente = _drouot_vente()
        lots = [_drouot_lot(12, "1 B SOME WINE - 2010 - Domaine Y",
                            number_extension="bis")]
        html = _drouot_gateway_html(vente, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        self.assertEqual(result.data["lots"][0]["lot_no"], "12bis")

    def test_no_pagination_request_is_made(self):
        vente = _drouot_vente()
        lots = [_drouot_lot(i, f"1 B WINE {i}") for i in range(1, 4)]
        html = _drouot_gateway_html(vente, lots)
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        result = AguttesFetcher().fetch(session, ref)
        self.assertEqual(len(result.data["lots"]), 3)
        self.assertEqual(session.requests, [(ref.url, 1)])

    def test_neither_shape_present_raises(self):
        html = _next_data_html({"props": {"pageProps": {
            "auction": None, "auctionLots": None,
            "drouotVente": None, "drouotLots": None,
        }}})
        ref = self._ref()
        session = FakeSession(catalogue_pages={(ref.url, 1): html})
        with self.assertRaises(MalformedResponse):
            AguttesFetcher().fetch(session, ref)


class PremiumRateTests(unittest.TestCase):
    def test_no_premiums_returns_none(self):
        self.assertIsNone(_premium_rate_ht([], 100.0))

    def test_no_hammer_price_returns_none(self):
        self.assertIsNone(_premium_rate_ht(
            [{"percent": 21, "amount_over": 0}], None))

    def test_picks_the_highest_applicable_tier(self):
        premiums = [{"percent": 25, "amount_over": 0},
                   {"percent": 20, "amount_over": 10000}]
        self.assertEqual(_premium_rate_ht(premiums, 9999.0), 0.25)
        self.assertEqual(_premium_rate_ht(premiums, 10000.0), 0.20)
        self.assertEqual(_premium_rate_ht(premiums, 50000.0), 0.20)


if __name__ == "__main__":
    unittest.main()
