import unittest
from unittest.mock import patch

from ingest.fetchers.drouot_template import DrouotTemplateFetcher, _num
from ingest.models import AuctionRef

BASE_URL = "https://www.art-richelieu.fr"
LISTING_URL = f"{BASE_URL}/ventes-passees"
CATALOGUE_URL = f"{BASE_URL}/catalogue/185292-vin-and-spiritueux"

LISTING_BARE_HTML = """
<a href="http://art-richelieu.fr/ventes-passees?year=2025">2025</a>
<a href="http://art-richelieu.fr/ventes-passees?year=2026">2026</a>
"""

LISTING_2026_HTML = """
<div class="calendrier entry clearfix Vente185292 Etude1" id="185292">
  <div class="entry-title"><h2>
    <a href="/catalogue/185292-vin-and-spiritueux">Vin &amp; spiritueux online</a>
  </h2></div>
</div>
<div class="calendrier entry clearfix Vente185300 Etude1" id="185300">
  <div class="entry-title"><h2>
    <a href="/catalogue/185300-bijoux-anciens">Bijoux anciens</a>
  </h2></div>
</div>
"""

LISTING_2025_HTML = """
<div class="calendrier entry clearfix Vente180000 Etude1" id="180000">
  <div class="entry-title"><h2>
    <a href="/catalogue/180000-tableaux">Tableaux et mobilier</a>
  </h2></div>
</div>
"""


def _card(lot_no, lot_id, grid_text, estimate, result=None,
         explication="Résultats sans frais"):
    flash = ""
    if result is not None:
        flash = f"""
            <div class="sale-flash2">Résultat<nobr>{result} EUR</nobr></div>
            <div class="explicationResultats">{explication}</div>
        """
    return f"""
    <div class="ordre_false product clearfix vente185292" id="lot{lot_no} lotId{lot_id}">
        <div class="product-desc">
            <div class="num_lot"><span class='lotnum'>{lot_no}</span></div>
            <div class="product-description">
                <a href="/lot/185292/{lot_id}-slug">
                    <h2 id="lotDesc-{lot_id}">{grid_text}</h2>
                </a>
            </div>
            <div class="product-price">
                <div class="estimAff4">{estimate} EUR</div>
                {flash}
            </div>
        </div>
    </div>
    """


CATALOGUE_PAGE0_HTML = f"""
<h1 class="nom_vente">Vin &amp; spiritueux online</h1>
<div class="date_vente">mardi 29 septembre 2026 10:00</div>
<p>Vente Frais de vente : 28% TTC. Enchères ouvertes dès le 15 septembre 2026.</p>
<div class="nbre_lot_haut">Lots 1 à 3 sur 3</div>
{_card(1, "111", "2 Bouteilles de Château...", "10 - 12", result="30")}
{_card(2, "112", "Bague en or jaune...", "100 - 150")}
{_card(3, "113", "3 Bouteilles de Château...", "20 - 30")}
"""

CATALOGUE_PAGE_EMPTY_HTML = "<div class='no-more'></div>"

LOT_111_DETAIL_HTML = (
    "<h1>2 Bouteilles de Château Margaux 1971 Premier Grand Cru "
    "Classé - Lot 1</h1>")
LOT_113_DETAIL_HTML = (
    "<h1>3\tBouteilles de Château Something\t\t1998 - Lot 3</h1>")


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, pages):
        self._pages = pages
        self.requests = []

    def get(self, url, params=None):
        self.requests.append((url, params))
        key = (url, tuple(sorted(params.items())) if params else None)
        value = self._pages.get(key, "")
        # A list of pages for one key is consumed in order (one entry
        # per call to that same URL+params) -- used to simulate a
        # transient empty page followed by a successful retry.
        if isinstance(value, list):
            return FakeResponse(value.pop(0) if value else "")
        return FakeResponse(value)


def fetcher():
    return DrouotTemplateFetcher(
        provider="art-richelieu", base_url=BASE_URL,
        results_path="/ventes-passees")


class TestNumParsing(unittest.TestCase):
    def test_strips_nbsp_thousands_separator(self):
        # Confirmed real: "sur 1\xa0050" and "4 150 EUR" both use a
        # non-breaking space as the thousands separator -- a plain
        # ``\d+`` match would silently read "1\xa0050" as just "1".
        self.assertEqual(_num("1\xa0050"), 1050.0)
        self.assertEqual(_num("4 150"), 4150.0)

    def test_handles_decimal_comma(self):
        self.assertEqual(_num("12,5"), 12.5)

    def test_none_for_empty(self):
        self.assertIsNone(_num(""))
        self.assertIsNone(_num(None))


class TestDiscover(unittest.TestCase):
    def test_reads_year_links_and_filters_titles(self):
        session = FakeSession({
            (LISTING_URL, None): LISTING_BARE_HTML,
            (LISTING_URL, (("year", 2025),)): LISTING_2025_HTML,
            (LISTING_URL, (("year", 2026),)): LISTING_2026_HTML,
        })
        refs = fetcher().discover(session)
        self.assertEqual([r.auction_id for r in refs], ["185292"])
        self.assertEqual(refs[0].title, "Vin & spiritueux online")

    def test_vinyles_title_is_not_mistaken_for_wine(self):
        # "vinyles" (vinyl records) must not match the \bvins?\b word
        # boundary -- a real Art Richelieu catalogue title.
        session = FakeSession({
            (LISTING_URL, None): "",
            (LISTING_URL, (("year", 2026),)):
                '<div class="calendrier entry clearfix" id="1">'
                '<div class="entry-title"><h2>'
                '<a href="/catalogue/1-vinyles-dete">Vinyles d’été</a>'
                '</h2></div></div>',
        })
        refs = fetcher().discover(session)
        self.assertEqual(refs, [])


class TestFetch(unittest.TestCase):
    def _fetch(self, extra_pages=None):
        pages = {
            (CATALOGUE_URL, (("max", 50), ("offset", 0))):
                CATALOGUE_PAGE0_HTML,
            (CATALOGUE_URL, (("max", 50), ("offset", 50))):
                CATALOGUE_PAGE_EMPTY_HTML,
            (f"{BASE_URL}/lot/185292/111-slug", None): LOT_111_DETAIL_HTML,
            (f"{BASE_URL}/lot/185292/113-slug", None): LOT_113_DETAIL_HTML,
        }
        if extra_pages:
            pages.update(extra_pages)
        ref = AuctionRef("art-richelieu", "185292", url=CATALOGUE_URL,
                         title="Vin & spiritueux online")
        session = FakeSession(pages)
        return fetcher().fetch(session, ref), session

    def test_non_wine_lot_is_dropped_without_a_detail_fetch(self):
        result, session = self._fetch()
        lot_ids = [r[0] for r in session.requests if "/lot/" in r[0]]
        self.assertNotIn(f"{BASE_URL}/lot/185292/112-slug", lot_ids)
        self.assertEqual(len(result.data["lots"]), 2)

    def test_full_untruncated_title_from_detail_page(self):
        # The grid card's own title is truncated server-side; the full
        # text (and therefore the vintage) only exists on the detail
        # page.
        result, _ = self._fetch()
        lot = result.data["lots"][0]
        self.assertEqual(
            lot["wine"],
            "2 Bouteilles de Château Margaux 1971 Premier Grand Cru "
            "Classé")
        self.assertEqual(lot["vintage"], "1971")
        self.assertEqual(lot["quantity"], 2)

    def test_sold_lot_has_hammer_price(self):
        result, _ = self._fetch()
        lot = result.data["lots"][0]
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["hammer_price"], 30.0)
        self.assertEqual(lot["estimate_low"], 10.0)
        self.assertEqual(lot["estimate_high"], 12.0)

    def test_unsold_lot_has_no_hammer_price(self):
        result, _ = self._fetch()
        lot = result.data["lots"][1]
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["hammer_price"])

    def test_detail_page_lot_suffix_and_tabs_are_stripped(self):
        # Confirmed real on every house checked: the detail page's own
        # <h1> appends " - Lot N" and uses literal tabs between fields --
        # neither belongs in the stored wine text.
        result, _ = self._fetch()
        lot = result.data["lots"][1]
        self.assertEqual(lot["wine"],
                         "3 Bouteilles de Château Something 1998")

    def test_auction_meta(self):
        result, _ = self._fetch()
        auction = result.data["auction"]
        self.assertEqual(auction["date"], "2026-09-29")
        self.assertEqual(auction["premium_rate"], 0.28)
        self.assertEqual(auction["currency"], "EUR")

    def test_raises_on_lot_count_mismatch(self):
        # Same failure class as whiskyauction.py's "Showing N of TOTAL"
        # check -- a page returning fewer cards than advertised could
        # otherwise be a silently truncated (blocked/challenge) fetch.
        mismatched = CATALOGUE_PAGE0_HTML.replace(
            "Lots 1 à 3 sur 3", "Lots 1 à 3 sur 4")
        with self.assertRaises(RuntimeError):
            self._fetch({
                (CATALOGUE_URL, (("max", 50), ("offset", 0))): mismatched,
            })

    def test_raises_when_result_label_is_not_sans_frais(self):
        unexpected = CATALOGUE_PAGE0_HTML.replace(
            "Résultats sans frais", "Résultats avec frais")
        with self.assertRaises(RuntimeError):
            self._fetch({
                (CATALOGUE_URL, (("max", 50), ("offset", 0))): unexpected,
            })

    def test_nc_result_is_treated_as_no_hammer_price_not_an_error(self):
        # Confirmed real: a Résultat block can read "NC" (Non
        # Communiqué) instead of a figure, with no
        # explicationResultats div at all -- the lot's result exists
        # but wasn't disclosed. Must not be mistaken for the
        # not-sans-frais anomaly (no figure to trust either way), and
        # must not raise.
        nc_card = """
        <div class="ordre_false product clearfix vente185292" id="lot1 lotId111">
            <div class="product-desc">
                <div class="num_lot"><span class='lotnum'>1</span></div>
                <div class="product-description">
                    <a href="/lot/185292/111-slug">
                        <h2 id="lotDesc-111">2 Bouteilles de Château...</h2>
                    </a>
                </div>
                <div class="product-price">
                    <div class="estimAff4">10 - 12 EUR</div>
                    <div class="sale-flash2"> Résultat <nobr> : NC </nobr> </div>
                </div>
            </div>
        </div>
        """
        page = (
            '<h1 class="nom_vente">Vin</h1>'
            '<div class="date_vente">mardi 29 septembre 2026 10:00</div>'
            '<div class="nbre_lot_haut">Lots 1 à 1 sur 1</div>'
            + nc_card)
        result, _ = self._fetch({
            (CATALOGUE_URL, (("max", 50), ("offset", 0))): page,
        })
        lot = result.data["lots"][0]
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["hammer_price"])

    def test_unrecognized_result_text_still_raises(self):
        # Code-review finding: only the specific, confirmed-real "NC"
        # value may skip the "sans frais" check without raising -- any
        # OTHER non-numeric text (a typo, "Retiré", a wording this
        # fetcher has never seen) must still fail loud instead of
        # being silently recorded as an unsold lot.
        weird_card = """
        <div class="ordre_false product clearfix vente185292" id="lot1 lotId111">
            <div class="product-desc">
                <div class="num_lot"><span class='lotnum'>1</span></div>
                <div class="product-description">
                    <a href="/lot/185292/111-slug">
                        <h2 id="lotDesc-111">2 Bouteilles de Château...</h2>
                    </a>
                </div>
                <div class="product-price">
                    <div class="estimAff4">10 - 12 EUR</div>
                    <div class="sale-flash2"> Résultat <nobr>Retiré</nobr> </div>
                </div>
            </div>
        </div>
        """
        page = (
            '<h1 class="nom_vente">Vin</h1>'
            '<div class="date_vente">mardi 29 septembre 2026 10:00</div>'
            '<div class="nbre_lot_haut">Lots 1 à 1 sur 1</div>'
            + weird_card)
        with self.assertRaises(RuntimeError):
            self._fetch({
                (CATALOGUE_URL, (("max", 50), ("offset", 0))): page,
            })

    @patch("ingest.fetchers.drouot_template.time.sleep")
    def test_retries_a_transient_empty_page_before_trusting_it(
            self, _mock_sleep):
        # Confirmed real during a full historical crawl: a page past
        # offset=0 occasionally came back with zero cards even though
        # the catalogue's own total said more remain; an isolated
        # re-fetch of the exact same URL immediately afterwards
        # returned the normal cards. _fetch_catalogue_page must retry
        # rather than trust the first empty response as "no more
        # pages" whenever the total is already known to be bigger.
        f = fetcher()
        ref = AuctionRef("art-richelieu", "185292", url=CATALOGUE_URL,
                         title="Vin & spiritueux online")
        key = (CATALOGUE_URL, (("max", 50), ("offset", 50)))
        session = FakeSession({
            key: [CATALOGUE_PAGE_EMPTY_HTML, CATALOGUE_PAGE0_HTML],
        })
        soup = f._fetch_catalogue_page(session, ref, 50, expected_total=100)
        self.assertEqual(len(soup.select("div.product.clearfix")), 3)
        self.assertEqual(len(session.requests), 2)

    @patch("ingest.fetchers.drouot_template.time.sleep")
    def test_retries_a_transient_empty_page_zero_too(self, _mock_sleep):
        # Confirmed real: several maisons-laffitte catalogues came back
        # with zero cards on a plain PAGE 0 fetch (no "Lots X à Y sur
        # N" ground truth yet either) during a full historical crawl,
        # but an isolated re-fetch of the exact same URL immediately
        # afterwards returned the normal lot grid -- page 0 must retry
        # an empty response too, not just later pages.
        f = fetcher()
        ref = AuctionRef("art-richelieu", "185292", url=CATALOGUE_URL,
                         title="Vin & spiritueux online")
        key = (CATALOGUE_URL, (("max", 50), ("offset", 0)))
        session = FakeSession({
            key: [CATALOGUE_PAGE_EMPTY_HTML, CATALOGUE_PAGE0_HTML],
        })
        soup = f._fetch_catalogue_page(session, ref, 0, expected_total=None)
        self.assertEqual(len(soup.select("div.product.clearfix")), 3)
        self.assertEqual(len(session.requests), 2)

    def test_does_not_retry_a_genuinely_empty_final_page(self):
        # Once offset has reached the known total, a page with zero
        # cards IS the real end of pagination -- retrying it would
        # just waste requests for no reason.
        f = fetcher()
        ref = AuctionRef("art-richelieu", "185292", url=CATALOGUE_URL,
                         title="Vin & spiritueux online")
        key = (CATALOGUE_URL, (("max", 50), ("offset", 50)))
        session = FakeSession({key: [CATALOGUE_PAGE_EMPTY_HTML]})
        soup = f._fetch_catalogue_page(session, ref, 50, expected_total=50)
        self.assertEqual(soup.select("div.product.clearfix"), [])
        self.assertEqual(len(session.requests), 1)


if __name__ == "__main__":
    unittest.main()
