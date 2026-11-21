# pylint: disable=protected-access
import unittest

from ingest.fetchers.astebolaffi import (
    START_ID, AsteBolaffiFetcher, MalformedResponse, ReconciliationMismatch,
    _margin_commission,
)
from ingest.models import AuctionRef


def _auction_page_html(title, start_date, end_date=None):
    end = end_date or start_date
    return (
        f"<title>{title} | Aste Bolaffi</title>"
        "<script>"
        f"$(\"#start_date\").text(getLocationDate('{start_date} 10:00:00'));"
        f"$(\"#end_date\").text('/ ' + getLocationDate('{end} 16:00:00'));"
        "</script>"
    )


def _redirect_html():
    return "<title>Redirecting to https://www.astebolaffi.it</title>"


def _lot_row(lot_no, desc, base_price=None, hammer_price=None,
            ordinary_vat=None):
    price_bits = ""
    if base_price is not None:
        price_bits += f'Base asta: <span class="asta-euro">&euro; {base_price}</span>'
    if hammer_price is not None:
        price_bits += (
            f' <span class="cms-gold">|</span> Aggiudicato a : '
            f'<span class="asta-euro">&euro; {hammer_price}</span>')
        if ordinary_vat:
            rate, vat_hammer, vat_premium = ordinary_vat
            title = (
                f"Regime di fatturazione con IVA ordinaria.<br />"
                f"Il prezzo di aggiudicazione sarà maggiorato di:<br />"
                f"1. Commissioni d’asta al {rate}%<br />"
                f"2. IVA sul prezzo di aggiudicazione alle seguenti "
                f"aliquote:<br />libri 4%<br />francobolli 10% <br />"
                f"tutte le altre categorie {vat_hammer}%<br />"
                f"3. IVA al {vat_premium}% sulle commissioni")
            price_bits += (
                ' <span style="font-family: \'Wingdings 2\'; color: red;">'
                '&#61617;</span> '
                f'<span data-toggle="tooltip" title="{title}">'
                'Più IVA ordinaria</span>')
    return (
        '<div class="row sezione-news lot-row">'
        '<div class="news-left lot-description">'
        f'<h5 class="asta-title"><a href="/it/lot/x/{lot_no}/detail">'
        f'Lotto {lot_no}</a></h5>'
        f'<p class="lot-dida">{desc}</p>'
        f'<p>{price_bits}</p>'
        '</div></div>'
    )


def _catalogue_html(rows):
    return "<html><body>" + "".join(rows) + "</body></html>"


class FakeSession:
    def __init__(self, pages=None):
        self._pages = pages or {}
        self.requests = []

    def get(self, url, params=None):
        page = (params or {}).get("page")
        key = (url, page) if page is not None else url
        self.requests.append(key)
        return _FakeResponse(self._pages.get(key, _redirect_html()))


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class DiscoverTests(unittest.TestCase):
    def test_keeps_only_concluded_wine_titled_auctions(self):
        pages = {
            f"https://www.astebolaffi.it/it/auction/{START_ID}":
                _auction_page_html("ASTA VINI PREGIATI", "2020-01-01"),
            f"https://www.astebolaffi.it/it/auction/{START_ID + 1}":
                _auction_page_html("ASTA DISTILLATI", "2099-01-01"),
        }
        session = FakeSession(pages=pages)
        refs = AsteBolaffiFetcher().discover(session)
        self.assertEqual(len(refs), 1)
        self.assertEqual(refs[0].auction_id, str(START_ID))
        self.assertEqual(refs[0].date, "2020-01-01")

    def test_stops_after_consecutive_non_wine_misses(self):
        pages = {
            f"https://www.astebolaffi.it/it/auction/{START_ID}":
                _auction_page_html("ASTA VINI", "2020-01-01"),
        }
        session = FakeSession(pages=pages)
        refs = AsteBolaffiFetcher().discover(session)
        self.assertEqual(len(refs), 1)
        # START_ID + 1 .. START_ID + 5 are all redirects (misses) -> stop.
        self.assertEqual(len(session.requests), 6)

    def test_upcoming_auction_with_future_end_date_is_skipped(self):
        pages = {
            f"https://www.astebolaffi.it/it/auction/{START_ID}":
                _auction_page_html("ASTA VINI", "2099-01-01", "2099-01-02"),
        }
        session = FakeSession(pages=pages)
        refs = AsteBolaffiFetcher().discover(session)
        self.assertEqual(refs, [])


class FetchTests(unittest.TestCase):
    def _ref(self, auction_id="606"):
        return AuctionRef(
            provider="astebolaffi", auction_id=auction_id,
            url=f"https://www.astebolaffi.it/it/auction/{auction_id}",
            title="ASTA VINI", date="2017-05-26")

    def test_sold_lot_under_margin_scheme_uses_tiered_commission(self):
        html = _catalogue_html([_lot_row(
            "1", "Barolo Riserva 2009, Cav. Lorenzo Accomasso (1 bt)",
            base_price="100", hammer_price="125")])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        result = AsteBolaffiFetcher().fetch(session, ref)

        self.assertEqual(result.data["auction"], {
            "id": "606", "name": "ASTA VINI", "date": "2017-05-26",
            "currency": "EUR",
        })
        lot = result.data["lots"][0]
        self.assertEqual(lot["lot_no"], "1")
        self.assertEqual(lot["vintage"], "2009")
        self.assertEqual(lot["quantity"], 1)
        self.assertEqual(lot["estimate_low"], 100.0)
        self.assertEqual(lot["hammer_price"], 125.0)
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["buyer_premium"], 31.25)  # 25% margin tier
        self.assertEqual(lot["vat_on_hammer"], 0.0)
        self.assertEqual(lot["vat_on_premium"], 0.0)

    def test_sold_lot_under_ordinary_vat_reads_rates_from_tooltip(self):
        html = _catalogue_html([_lot_row(
            "6", "Barolo 2016, Cascina Nuova (4 bts)",
            base_price="200", hammer_price="200",
            ordinary_vat=(18, 22, 22))])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        result = AsteBolaffiFetcher().fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertEqual(lot["buyer_premium"], 36.0)  # 200 * 18%
        self.assertEqual(lot["vat_on_hammer"], 44.0)  # 200 * 22%
        self.assertEqual(lot["vat_on_premium"], 7.92)  # 36 * 22%

    def test_unsold_lot_has_no_hammer_or_premium(self):
        html = _catalogue_html([_lot_row(
            "2", "Barbera d'Alba 2018 (2 bts)", base_price="50")])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        result = AsteBolaffiFetcher().fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["hammer_price"])
        self.assertIsNone(lot["buyer_premium"])

    def test_total_bottle_count_preferred_over_sub_counts(self):
        desc = ("Barbera d'Alba 2016 (1 bt) Spalla alta 2017 (1 bt) "
               "(Tot. 2 bts)")
        html = _catalogue_html([_lot_row("1", desc, base_price="50")])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        result = AsteBolaffiFetcher().fetch(session, ref)
        self.assertEqual(result.data["lots"][0]["quantity"], 2)

    def test_magnum_and_double_magnum_quantity_units(self):
        html = _catalogue_html([
            _lot_row("1", "Paleo 1998 (1 Mag)", base_price="100"),
            _lot_row("2", "Sassicaia 2001 (2 DMag)", base_price="200"),
        ])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        result = AsteBolaffiFetcher().fetch(session, ref)
        self.assertEqual(result.data["lots"][0]["quantity"], 1)
        self.assertEqual(result.data["lots"][1]["quantity"], 2)

    def test_multiple_sold_vintages_in_one_lot_leaves_vintage_null(self):
        desc = ("Pavillon Rouge 1998 (4 bts) Pavillon Rouge 1988 (1 bt) "
               "(Tot. 5 bts)")
        html = _catalogue_html([_lot_row("1", desc, base_price="200")])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        result = AsteBolaffiFetcher().fetch(session, ref)
        self.assertIsNone(result.data["lots"][0]["vintage"])

    def test_paginates_until_a_short_page(self):
        full_page = _catalogue_html(
            [_lot_row(str(i), f"Wine {i} (1 bt)", base_price="10")
             for i in range(1, 11)])
        short_page = _catalogue_html(
            [_lot_row("11", "Wine 11 (1 bt)", base_price="10")])
        ref = self._ref()
        session = FakeSession(pages={
            (ref.url, 1): full_page, (ref.url, 2): short_page})
        result = AsteBolaffiFetcher().fetch(session, ref)
        self.assertEqual(len(result.data["lots"]), 11)

    def test_duplicate_lot_numbers_across_pagination_raises(self):
        page1 = _catalogue_html(
            [_lot_row(str(i), f"Wine {i} (1 bt)", base_price="10")
             for i in range(1, 11)])
        # A short second page that (wrongly) repeats lot 1 -- a
        # pagination bug, not a real auction, must fail loud.
        page2 = _catalogue_html([_lot_row("1", "Wine 1 (1 bt)",
                                          base_price="10")])
        ref = self._ref()
        session = FakeSession(pages={
            (ref.url, 1): page1, (ref.url, 2): page2})
        with self.assertRaises(ReconciliationMismatch):
            AsteBolaffiFetcher().fetch(session, ref)

    def test_lot_row_with_no_parseable_lot_number_raises(self):
        html = _catalogue_html(['<div class="row sezione-news lot-row">'
                                '<div class="news-left lot-description">'
                                '<h5 class="asta-title"><a href="#">'
                                '</a></h5>'
                                '<p class="lot-dida">Wine (1 bt)</p>'
                                '<p>Base asta: '
                                '<span class="asta-euro">&euro; 50</span>'
                                '</p></div></div>'])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        with self.assertRaises(MalformedResponse):
            AsteBolaffiFetcher().fetch(session, ref)

    def test_no_lot_rows_raises(self):
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): "<html></html>"})
        with self.assertRaises(MalformedResponse):
            AsteBolaffiFetcher().fetch(session, ref)

    def test_sold_lot_with_no_second_price_raises(self):
        # "Aggiudicato a" text present but no second .asta-euro span --
        # malformed/unexpected markup, must fail loud not guess.
        html = _catalogue_html(['<div class="row sezione-news lot-row">'
                                '<div class="news-left lot-description">'
                                '<h5 class="asta-title"><a href="#">'
                                'Lotto 1</a></h5>'
                                '<p class="lot-dida">Wine (1 bt)</p>'
                                '<p>Base asta: '
                                '<span class="asta-euro">&euro; 50</span>'
                                ' Aggiudicato a</p></div></div>'])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        with self.assertRaises(MalformedResponse):
            AsteBolaffiFetcher().fetch(session, ref)

    def test_unparseable_ordinary_vat_tooltip_raises(self):
        html = _catalogue_html(['<div class="row sezione-news lot-row">'
                                '<div class="news-left lot-description">'
                                '<h5 class="asta-title"><a href="#">'
                                'Lotto 1</a></h5>'
                                '<p class="lot-dida">Wine (1 bt)</p>'
                                '<p>Base asta: '
                                '<span class="asta-euro">&euro; 50</span>'
                                ' Aggiudicato a : '
                                '<span class="asta-euro">&euro; 60</span>'
                                ' <span data-toggle="tooltip" '
                                'title="some unexpected wording">'
                                'Più IVA ordinaria</span>'
                                '</p></div></div>'])
        ref = self._ref()
        session = FakeSession(pages={(ref.url, 1): html})
        with self.assertRaises(MalformedResponse):
            AsteBolaffiFetcher().fetch(session, ref)


class MarginCommissionTests(unittest.TestCase):
    def test_flat_first_tier(self):
        self.assertEqual(_margin_commission(5000), 1250.0)  # 25%

    def test_progressive_across_tiers(self):
        # 250000*0.25 + 50000*0.225 = 62500 + 11250 = 73750
        self.assertEqual(_margin_commission(300000), 73750.0)


if __name__ == "__main__":
    unittest.main()
