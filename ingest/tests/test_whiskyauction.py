import unittest

from ingest.fetchers.whiskyauction import WhiskyAuctionFetcher
from ingest.models import AuctionRef

AUCTIONS_HTML = """
<div class="auctionentry">
  <a href="/auctions/auction/198">
    <span class="auctionentry-title"><span class="auctionentry-title-main">June 2026 - Fine &amp; Rare Wines</span></span>
  </a>
  <div class="block auction-date-end"><span class="enddate label">Ended</span> <span class="value">23 Jun 2026</span></div>
</div>
<div class="auctionentry">
  <a href="/auctions/auction/204">
    <span class="auctionentry-title"><span class="auctionentry-title-main">November 2026 - Whisky &amp; Spirits</span></span>
  </a>
  <div class="block auction-date-end"><span class="enddate label">Ended</span> <span class="value">03 Nov 2026</span></div>
</div>
"""

LOTS_HTML = """
<div id="lot_221959" class="lot lotItem CR Met" data-winningbid="3500.00"
     data-enddate="2026-06-23 20:10:00">
    <span class="lotName1 lot-title-main">2001 Grands Echezeaux Magnum</span>
    <span class="lotName2 lot-title-sup">Domaine De La Romanee Conti</span>
    <span class="lotName3 lot-title-sup">150cl / 13%</span>
</div>
<div id="lot_221566" class="lot lotItem CR NA" data-winningbid="2300.00"
     data-enddate="2026-06-23 20:50:00">
    <span class="lotName1 lot-title-main">2018 Chateau Mouton Rothschild</span>
    <span class="lotName2 lot-title-sup">Premier Grand Cru Classe - Pauillac</span>
    <span class="lotName3 lot-title-sup">6 x 75cl / 14%</span>
</div>
<div id="lot_221600" class="lot lotItem CR NotMet" data-winningbid="400.00"
     data-enddate="2026-06-23 20:50:00">
    <span class="lotName1 lot-title-main">Laurent Perrier Cuvee Rose</span>
    <span class="lotName2 lot-title-sup"></span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
"""

TRAILING_VINTAGE_HTML = """
<div id="lot_95799" class="lot lotItem CR Met" data-winningbid="3600.00"
     data-enddate="2020-11-24 18:00:00">
    <span class="lotName1 lot-title-main">Chateau Margaux 1989</span>
    <span class="lotName2 lot-title-sup">Premier Grand Cru Classe</span>
    <span class="lotName3 lot-title-sup">12 x 75cl / 12.5%</span>
</div>
<div id="lot_200001" class="lot lotItem CR Met" data-winningbid="900.00"
     data-enddate="2020-11-24 18:00:00">
    <span class="lotName1 lot-title-main">1987 Montecillo Vina Monty Gran Reserva &amp; 1991 Montecillo Vina Cumbrero Rioja</span>
    <span class="lotName2 lot-title-sup"></span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
<div id="lot_200002" class="lot lotItem CR Met" data-winningbid="800.00"
     data-enddate="2020-11-24 18:00:00">
    <span class="lotName1 lot-title-main">1997 Florio Targa Riserva 1840 Marsala Superiore</span>
    <span class="lotName2 lot-title-sup"></span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
"""

SHOWING_MISMATCH_HTML = LOTS_HTML + """
<div class="detail-showing">
    Showing <span>1</span> <span>to </span><span>3</span>
    <span>of </span><span>5</span>
</div>
"""

OPEN_STATUS_HTML = """
<div id="lot_9" class="lot lotItem CR Met" data-winningbid="100.00"
     data-enddate="2026-06-23 20:10:00" data-auction-status="Open">
    <span class="lotName1 lot-title-main">2020 Some Wine</span>
    <span class="lotName2 lot-title-sup"></span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
"""

PRODUCER_HTML = """
<div id="lot_1" class="lot lotItem CR Met" data-winningbid="100.00"
     data-enddate="2026-06-23 20:10:00">
    <span class="lotName1 lot-title-main">2015 Musigny Grand Cru</span>
    <span class="lotName2 lot-title-sup">Jacques Frederic Mugnier - 100 Points</span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
"""

CLOS_HTML = """
<div id="lot_1" class="lot lotItem CR Met" data-winningbid="500.00"
     data-enddate="2026-06-23 20:10:00">
    <span class="lotName1 lot-title-main">Clos De La Roche Grand Cru</span>
    <span class="lotName2 lot-title-sup">Domaine Armand Rousseau</span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
<div id="lot_2" class="lot lotItem CR Met" data-winningbid="600.00"
     data-enddate="2026-06-23 20:10:00">
    <span class="lotName1 lot-title-main">Clos Vougeot Grand Cru</span>
    <span class="lotName2 lot-title-sup">Chateau De La Tour</span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
<div id="lot_3" class="lot lotItem CR Met" data-winningbid="700.00"
     data-enddate="2026-06-23 20:10:00">
    <span class="lotName1 lot-title-main">Clos Des Papes</span>
    <span class="lotName2 lot-title-sup">Chateauneuf Du Pape</span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
<div id="lot_4" class="lot lotItem CR Met" data-winningbid="800.00"
     data-enddate="2026-06-23 20:10:00">
    <span class="lotName1 lot-title-main">Clos Du Marquis 2000</span>
    <span class="lotName2 lot-title-sup">Saint-Julien</span>
    <span class="lotName3 lot-title-sup">75cl</span>
</div>
"""

EMPTY_HTML = "<div class='no-lots'></div>"


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, pages):
        self._pages = pages
        self.requests = []

    def get(self, url, params=None):
        self.requests.append((url, params))
        key = (url, params.get("pageIndex") if params else None)
        return FakeResponse(self._pages.get(key, ""))


class TestWhiskyAuctionDiscover(unittest.TestCase):
    def test_filters_to_wine_titled_auctions(self):
        f = WhiskyAuctionFetcher()
        session = FakeSession({
            ("https://whisky.auction/auctions", None): AUCTIONS_HTML})
        refs = f.discover(session)
        self.assertEqual([r.auction_id for r in refs], ["198"])
        self.assertEqual(refs[0].title, "June 2026 - Fine & Rare Wines")
        self.assertEqual(refs[0].date, "23 Jun 2026")


class TestWhiskyAuctionFetch(unittest.TestCase):
    def _fetch(self, pages):
        f = WhiskyAuctionFetcher()
        ref = AuctionRef("whiskyauction", "198",
                         url="https://whisky.auction/auctions/auction/198",
                         title="June 2026 - Fine & Rare Wines")
        session = FakeSession(pages)
        return f.fetch(session, ref), session

    def test_paginates_until_empty_page(self):
        result, session = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        self.assertEqual(len(result.data["lots"]), 3)
        self.assertEqual(len(session.requests), 2)

    def test_requests_always_scope_to_wine_categories(self):
        _, session = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): EMPTY_HTML,
        })
        _, params = session.requests[0]
        self.assertIn("Champagne", params["category"])
        self.assertIn("Wine - Bordeaux", params["category"])
        self.assertEqual(params["pageSize"], 90)

    def test_sold_lot_fields(self):
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_no"], "221959")
        self.assertEqual(lot["wine"], "2001 Grands Echezeaux Magnum")
        self.assertEqual(lot["vintage"], "2001")
        self.assertEqual(lot["quantity"], 1)
        self.assertEqual(lot["bottle_size_cl"], 150.0)
        self.assertEqual(lot["abv"], 13.0)
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["hammer_price"], 3500.0)
        self.assertEqual(lot["lot_date"], "2026-06-23")

    def test_multi_bottle_quantity_from_format_text(self):
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        lot = result.data["lots"][1]
        self.assertEqual(lot["quantity"], 6)
        self.assertEqual(lot["bottle_size_cl"], 75.0)

    def test_reserve_not_met_lot_has_no_hammer_price(self):
        # Senior-review-style finding, confirmed against the real site's
        # own CSS: a NotMet lot's data-winningbid is only the highest
        # (losing) bid, not a real sale -- must not become a price.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        lot = result.data["lots"][2]
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["hammer_price"])

    def test_vintage_none_for_nv_champagne(self):
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        lot = result.data["lots"][2]
        self.assertIsNone(lot["vintage"])

    def test_vintage_found_at_end_of_title(self):
        # Confirmed real: older (pre-2021) auctions put the vintage at
        # the end ("Chateau Margaux 1989"), not the start.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0):
                TRAILING_VINTAGE_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        self.assertEqual(result.data["lots"][0]["vintage"], "1989")

    def test_vintage_none_when_title_has_multiple_year_like_numbers(self):
        # A genuinely bundled multi-vintage lot ("1987 ... & 1991 ...")
        # and a single-vintage lot whose product name happens to
        # contain an unrelated year-like number ("Targa Riserva 1840")
        # are indistinguishable from the title text alone -- both must
        # stay unresolved rather than guessing which number is real.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0):
                TRAILING_VINTAGE_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        self.assertIsNone(result.data["lots"][1]["vintage"])
        self.assertIsNone(result.data["lots"][2]["vintage"])

    def test_raises_when_lot_count_does_not_match_showing_total(self):
        # Senior-review finding: a page returning zero `.lot.lotItem`
        # cards normally means "no more pages", but a blocked/challenge
        # response on page 2+ would look identical -- cross-checking
        # against the site's own "Showing N of TOTAL" count catches a
        # truncated fetch instead of silently archiving it as complete.
        with self.assertRaises(RuntimeError):
            self._fetch({
                ("https://whisky.auction/auctions/auction/198", 0):
                    SHOWING_MISMATCH_HTML,
                ("https://whisky.auction/auctions/auction/198", 1):
                    EMPTY_HTML,
            })

    def test_raises_when_lot_has_non_close_auction_status(self):
        # A lot whose auction-status isn't "Close" means either a
        # still-open auction slipped past discover()'s scoping, or an
        # unexpected response shape -- must not be archived as a final
        # sale either way.
        with self.assertRaises(RuntimeError):
            self._fetch({
                ("https://whisky.auction/auctions/auction/198", 0):
                    OPEN_STATUS_HTML,
                ("https://whisky.auction/auctions/auction/198", 1):
                    EMPTY_HTML,
            })

    def test_producer_extracted_for_burgundy_style_title(self):
        # "Richebourg Grand Cru"-style titles don't self-identify a
        # producer -- lotName2 ("Domaine De La Romanee Conti") is one.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        self.assertEqual(result.data["lots"][0]["producer"],
                         "Domaine De La Romanee Conti")

    def test_producer_none_for_self_identifying_chateau_title(self):
        # "Chateau Mouton Rothschild" already names its own producer;
        # lotName2 here is appellation/classification text, not one.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): LOTS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        self.assertIsNone(result.data["lots"][1]["producer"])

    def test_producer_none_when_lotname2_has_a_critic_score(self):
        # "Jacques Frederic Mugnier - 100 Points" IS a real producer
        # name with a score suffix, but the digit makes it
        # indistinguishable from pure classification/score text --
        # left unresolved rather than guessed, like an ambiguous
        # vintage.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0):
                PRODUCER_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        self.assertIsNone(result.data["lots"][0]["producer"])

    def test_producer_extracted_for_shared_clos_vineyard(self):
        # "Clos De La Roche"/"Clos Vougeot" are Burgundy Grand Crus
        # farmed by several different domaines (confirmed live-site
        # crawl + data/reference/wines_by_producer.csv) -- unlike most
        # "Clos ..." titles, lotName2 here really is a producer name,
        # not appellation/classification text.
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): CLOS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        lots = result.data["lots"]
        self.assertEqual(lots[0]["producer"], "Domaine Armand Rousseau")
        self.assertEqual(lots[1]["producer"], "Chateau De La Tour")

    def test_producer_none_for_appellation_fronted_clos_title(self):
        # "Clos Des Papes"/"Clos Du Marquis" each name a single estate;
        # lotName2 there is the APPELLATION ("Chateauneuf Du Pape",
        # "Saint-Julien"), not a producer -- must stay self-identifying
        # even though neither appellation name contains a digit or a
        # "cru"/"classe"/"appellation" keyword for _NOT_PRODUCER to
        # catch (this is exactly the false-positive the narrow
        # _SHARED_CLOS_VINEYARDS allowlist exists to avoid).
        result, _ = self._fetch({
            ("https://whisky.auction/auctions/auction/198", 0): CLOS_HTML,
            ("https://whisky.auction/auctions/auction/198", 1): EMPTY_HTML,
        })
        lots = result.data["lots"]
        self.assertIsNone(lots[2]["producer"])
        self.assertIsNone(lots[3]["producer"])


if __name__ == "__main__":
    unittest.main()
