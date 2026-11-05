# pylint: disable=protected-access,unused-argument
# -- protected-access: testing _render/_iter_category_cards directly is the
# whole point of these tests; unused-argument: the fake _render() replacement
# matches the real one's full signature even when a given test only cares
# about one argument.
import datetime
import re
import unittest

from ingest.fetchers.bestwineauctions import (
    BestwineauctionsFetcher, _eur_amount, _volume_dl, parse_categories,
    parse_lot_cards, parse_lot_detail)
from ingest.models import AuctionRef

CATEGORIES_HTML = """
<nav>
<a href="https://auction.bestwineauctions.com/en/category/128/bordeaux-red">Bordeaux Red</a>
<a href="https://auction.bestwineauctions.com/en/category/130/burgundy-red">Burgundy Red</a>
<a href="https://auction.bestwineauctions.com/en/category/151/all-regions">Other</a>
<a href="https://auction.bestwineauctions.com/en/category/153/all-regions">Other2</a>
</nav>
"""

CATEGORY_PAGE_HTML = """
<div class="col-xl-3 col-lg-4 col-md-6 col-6 unprocessed-lotcard" style="opacity:.8;"><div class="product lot-card"><div class="lot-title"><a class="text-dark" href="https://auction.bestwineauctions.com/en/lot-details/111155/France/Bordeaux Red/bordeaux-10-bottles-1-magnum-mixed-mc-11-bottles">2220. BORDEAUX 10 BOTTLES + 1 MAGNUM MIXED - Mc - 11 Bottles</a></div><!--!-->
<div class="product-image img-lot-container overflow-hidden"><a href="https://auction.bestwineauctions.com/en/lot-details/111155/France/Bordeaux Red/bordeaux-10-bottles-1-magnum-mixed-mc-11-bottles"><img src="x.jpg"></a></div><!--!-->
<div class="lot-footer"><div class="lot-meta"><span class="lot-countdown is-closed">Closed 01 Jul 2026</span></div><!--!-->
<ul class="list-inline mb-0"><li class="list-inline-item row-label">Current bid</li><!--!-->
<li class="list-inline-item price">&euro;  150,00</li></ul></div></div></div>

<div class="col-xl-3 col-lg-4 col-md-6 col-6 unprocessed-lotcard"><div class="product lot-card"><div class="lot-title"><a class="text-dark" href="https://auction.bestwineauctions.com/en/lot-details/222222/France/Bordeaux Red/still-open-lot">2221. STILL OPEN LOT</a></div>
<div class="lot-footer"><div class="lot-meta"><span class="lot-countdown is-open">3d 4h left</span></div>
<ul class="list-inline mb-0"><li class="list-inline-item row-label">Current bid</li><li class="list-inline-item price">&euro;  10,00</li></ul></div></div></div>
"""

LOT_DETAIL_HTML = """
<ol class="breadcrumb"><li class="breadcrumb-item"><a href="https://auction.bestwineauctions.com/en/dashboard?auctionid=48">Exclusive Wine Auction 48</a></li><li class="breadcrumb-item active">BORDEAUX 10 BOTTLES</li></ol>
<h1 class="hero-heading h4 mb-3">2220 : BORDEAUX 10 BOTTLES + 1 MAGNUM MIXED - Mc - 11 Bottles</h1>
<div class="bwa-bidpanel " id="bgindicator"><div class="bwa-hero"><div class="bwa-hero-label">Current bid</div><!--!-->
<div class="bwa-hero-value" id="currentBid">150 &euro; </div>
<div class="bwa-hero-countdown timer" id="timer-x" data-seconds="-10720585">Closed</div></div></div>
<div class="bwa-total-bids"><span class="bwa-row-label">Total bids</span><span class="bwa-total-bids-value" id="totalBids">9</span></div>
<div class="bwa-rows">
<div class="bwa-row" id="show-startingbid-text"><span class="bwa-row-label">Starting bid</span><span class="bwa-row-value" id="startingBid">28 &euro; </span></div>
<div class="bwa-row"><span class="bwa-row-label">Next increment bid</span><span class="bwa-row-value" id="nextIncrementBid">160 &euro; </span></div>
<div class="bwa-row"><span class="bwa-row-label" title="t">VAT</span><span class="bwa-row-value">0 %</span></div>
<div class="bwa-row"><span class="bwa-row-label">Buyers premium</span><span class="bwa-row-value">19.5 %</span></div>
<div class="bwa-row"><span class="bwa-row-label" title="t">VAT over buyers premium</span><span class="bwa-row-value">21 %</span></div>
<div class="bwa-row"><span class="bwa-row-label">Estimate price low</span><span class="bwa-row-value" id="estimateLow">28 &euro; </span></div>
<div class="bwa-row"><span class="bwa-row-label">Estimate price high</span><span class="bwa-row-value" id="estimateHigh">39 &euro; </span></div>
</div>
<div class="bwa-time-rows">
<div class="bwa-row"><span class="bwa-row-label">Start time</span><span class="bwa-row-value" id="startTime">Jun 19, 2026  12:00</span></div>
<div class="bwa-row"><span class="bwa-row-label">Closing time</span><span class="bwa-row-value" id="closingTime">Jul 1, 2026  20:00</span></div>
</div>
<ul class="list-inline pb-2 mb-4 w-100 bg-light">
<li class="block-toggler text-white fw-bold mb-3 bg-theme p-2">Lot information</li>
<li class="detail-option-heading px-2 mb-3 h4 d-flex justify-content-between w-100">Bottler<!--!-->: <span><!--!-->Mc</span></li>
<li class="detail-option-heading px-2 mb-3 h4 d-flex justify-content-between w-100">Extra info<!--!-->: <span><!--!-->NR</span></li>
<li class="detail-option-heading px-2 mb-3 h4 d-flex justify-content-between w-100">Level<!--!-->: <span><!--!-->Neck</span></li>
<li class="detail-option-heading px-2 mb-3 h4 d-flex justify-content-between w-100">Label<!--!-->: <span><!--!-->GL</span></li>
<li class="detail-option-heading px-2 mb-3 h4 d-flex justify-content-between w-100">Volume<!--!-->: <span><!--!-->0,75</span></li>
<li class="detail-option-heading px-2 mb-3 h4 d-flex justify-content-between w-100">Appellation<!--!-->: <span><!--!-->Bordeaux</span></li>
</ul>
"""

LOT_DETAIL_OPEN_HTML = """
<div class="bwa-hero-countdown timer" data-seconds="86400">2d left</div>
"""


class EurAmountTest(unittest.TestCase):
    def test_thousands_dot_with_no_decimal_comma(self):
        """Confirmed real bug, caught live: a round-number bid on this
        site renders as "1.050 €" -- a thousands dot with NO decimal
        comma at all, not "1.050,00". Treating any lone dot as a decimal
        point silently divided every such amount by ~1000 -- confirmed
        in the archive itself: a real EUR2,695 Mouton Rothschild 1994
        lot (10 bottles) had been archived as hammer_price=2.695."""
        self.assertEqual(_eur_amount("1.050 €"), 1050.0)
        self.assertEqual(_eur_amount("2.695 €"), 2695.0)
        self.assertEqual(_eur_amount("1.234.567 €"), 1234567.0)

    def test_decimal_comma_with_thousands_dot_still_works(self):
        self.assertEqual(_eur_amount("1.050,50 €"), 1050.50)

    def test_decimal_comma_alone_still_works(self):
        self.assertEqual(_eur_amount("150,00 €"), 150.0)
        self.assertEqual(_eur_amount("12,5 €"), 12.5)

    def test_plain_amount_unaffected(self):
        self.assertEqual(_eur_amount("150 €"), 150.0)
        self.assertEqual(_eur_amount("28 €"), 28.0)


class VolumeDlTest(unittest.TestCase):
    def test_comma_decimal(self):
        self.assertEqual(_volume_dl("0,75"), 7.5)
        self.assertEqual(_volume_dl("1,5"), 15.0)

    def test_dot_decimal_is_not_mangled_by_the_eur_thousands_heuristic(self):
        """Confirmed real gap: _volume_dl used to reuse _eur_amount, whose
        thousands-dot heuristic (tuned for EUR amounts) strips a lone dot
        followed by exactly 3 digits as a thousands separator. A liter
        value is never in the thousands -- a future/unsampled category
        rendering Volume as "0.375" (half bottle, dot decimal) must parse
        to 3.75 dl, not be silently mangled to 3750.0 dl (1000x off)."""
        self.assertEqual(_volume_dl("0.375"), 3.75)
        self.assertEqual(_volume_dl("1.500"), 15.0)

    def test_keyword_fallback_still_works(self):
        self.assertEqual(_volume_dl("Magnum"), 15.0)
        self.assertEqual(_volume_dl("Jeroboam"), 30.0)
        self.assertEqual(_volume_dl("Half"), 3.75)

    def test_unparseable_returns_none(self):
        self.assertIsNone(_volume_dl("1* 0,375 + 1* 0,750Ltr"))
        self.assertIsNone(_volume_dl(None))
        self.assertIsNone(_volume_dl(""))


class ParseCategoriesTest(unittest.TestCase):
    def test_dedups_by_id_keeping_first_slug(self):
        cats = parse_categories(CATEGORIES_HTML)
        self.assertEqual(cats, [
            ("128", "bordeaux-red"), ("130", "burgundy-red"),
            ("151", "all-regions"), ("153", "all-regions"),
        ])


class ParseLotCardsTest(unittest.TestCase):
    def test_extracts_id_title_url_and_closed_state(self):
        cards = parse_lot_cards(CATEGORY_PAGE_HTML)
        self.assertEqual(len(cards), 2)
        self.assertEqual(cards[0]["lot_id"], "111155")
        self.assertTrue(cards[0]["closed"])
        self.assertIn("BORDEAUX 10 BOTTLES", cards[0]["title"])
        self.assertEqual(cards[1]["lot_id"], "222222")
        self.assertFalse(cards[1]["closed"])


class ParseLotDetailTest(unittest.TestCase):
    def test_parses_full_lot_with_computed_premium_and_tax(self):
        ref = AuctionRef(provider="bestwineauctions", auction_id="111155",
                         url="https://auction.bestwineauctions.com/en/"
                             "lot-details/111155/x")
        lot = parse_lot_detail(LOT_DETAIL_HTML, ref)
        self.assertIsNotNone(lot)
        self.assertEqual(lot["lot_no"], "2220")
        self.assertIn("BORDEAUX 10 BOTTLES", lot["wine"])
        self.assertEqual(lot["producer"], "Mc")
        self.assertEqual(lot["appellation"], "Bordeaux")
        self.assertEqual(lot["bottle_size_dl"], 7.5)
        self.assertEqual(lot["hammer_price"], 150.0)
        self.assertEqual(lot["estimate_low"], 28.0)
        self.assertEqual(lot["estimate_high"], 39.0)
        self.assertAlmostEqual(lot["buyer_premium"], 29.25)
        self.assertAlmostEqual(lot["tax_amount"], round(29.25 * 0.21, 2))
        self.assertAlmostEqual(lot["total_price"],
                               150.0 + 29.25 + round(29.25 * 0.21, 2))
        self.assertEqual(lot["price_basis"], "HAMMER")
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["_auction"]["id"], "48")
        self.assertEqual(lot["_auction"]["name"], "Exclusive Wine Auction 48")
        self.assertEqual(lot["_auction"]["date"], "2026-07-01")
        self.assertEqual(lot["_auction"]["start_date"], "2026-06-19")

    def test_zero_total_bids_is_not_sold_despite_nonzero_current_bid(self):
        """Confirmed real (live-checked 2026-11-03): #currentBid can equal
        the lot's own starting bid price even when it's genuinely unsold
        -- #totalBids is the actual bid count and the authoritative
        signal, not the bid amount."""
        html = LOT_DETAIL_HTML.replace(
            '<span class="bwa-total-bids-value" id="totalBids">9</span>',
            '<span class="bwa-total-bids-value" id="totalBids">0</span>')
        ref = AuctionRef(provider="bestwineauctions", auction_id="111155",
                         url="https://auction.bestwineauctions.com/en/"
                             "lot-details/111155/x")
        lot = parse_lot_detail(html, ref)
        self.assertFalse(lot["sold"])
        self.assertIsNone(lot["hammer_price"])
        self.assertIsNone(lot["buyer_premium"])
        self.assertEqual(lot["price_basis"], "UNKNOWN")

    def test_falls_back_to_hammer_heuristic_when_totalbids_missing(self):
        """If the site ever omits #totalBids, sold status still falls
        back to the old hammer>0 heuristic rather than defaulting to
        "never sold"."""
        html = LOT_DETAIL_HTML.replace(
            '<div class="bwa-total-bids"><span class="bwa-row-label">'
            'Total bids</span><span class="bwa-total-bids-value" '
            'id="totalBids">9</span></div>', '')
        ref = AuctionRef(provider="bestwineauctions", auction_id="111155",
                         url="https://auction.bestwineauctions.com/en/"
                             "lot-details/111155/x")
        lot = parse_lot_detail(html, ref)
        self.assertTrue(lot["sold"])
        self.assertEqual(lot["hammer_price"], 150.0)

    def test_returns_none_when_not_closed(self):
        ref = AuctionRef(provider="bestwineauctions", auction_id="999",
                         url="https://auction.bestwineauctions.com/en/"
                             "lot-details/999/x")
        self.assertIsNone(parse_lot_detail(LOT_DETAIL_OPEN_HTML, ref))

    def test_raises_rather_than_misgrouping_when_breadcrumb_missing(self):
        """Confirmed real risk (never actually observed in the first
        production run's 8645 lots, checked directly): the old fallback
        ("auction_id or ref.auction_id") would have silently keyed this
        lot under its own lot id as a bogus single-lot "auction" instead
        of erroring -- must raise so the caller skips it instead."""
        html = LOT_DETAIL_HTML.replace(
            '<ol class="breadcrumb"><li class="breadcrumb-item">'
            '<a href="https://auction.bestwineauctions.com/en/'
            'dashboard?auctionid=48">Exclusive Wine Auction 48</a>'
            '</li><li class="breadcrumb-item active">'
            'BORDEAUX 10 BOTTLES</li></ol>', '')
        ref = AuctionRef(provider="bestwineauctions", auction_id="111155",
                         url="https://auction.bestwineauctions.com/en/"
                             "lot-details/111155/x")
        with self.assertRaises(RuntimeError):
            parse_lot_detail(html, ref)


def _card_html(lot_id, closed_label):
    return (
        '<div class="product lot-card"><div class="lot-title">'
        f'<a class="text-dark" href="https://x/en/lot-details/{lot_id}/y">'
        f'T{lot_id}</a></div>'
        '<div class="lot-footer"><div class="lot-meta">'
        f'<span class="lot-countdown is-closed">{closed_label}</span>'
        '</div></div></div>')


class IterCategoryCardsTest(unittest.TestCase):
    def test_stops_once_a_page_is_entirely_older_than_cutoff(self):
        f = BestwineauctionsFetcher()
        pages = {
            1: "".join(_card_html(i, "Closed 01 Jul 2026") for i in (1, 2)),
            2: "".join(_card_html(i, "Closed 01 Jan 2020") for i in (3, 4)),
            3: "".join(_card_html(i, "Closed 01 Jan 2019") for i in (5, 6)),
        }
        rendered = []

        def fake_render(url, selector, timeout=15000, settle_js=None, attempts=2):
            n = int(re.search(r"page=(\d+)", url).group(1))
            rendered.append(n)
            return pages.get(n)

        f._render = fake_render
        cutoff = datetime.date(2026, 1, 1)
        cards = list(f._iter_category_cards("128", "bordeaux-red", cutoff))
        self.assertEqual([c["lot_id"] for c in cards], ["1", "2", "3", "4"])
        self.assertEqual(rendered, [1, 2])

    def test_stops_on_repeated_last_page_when_unbounded(self):
        """Confirmed real on the live site: past the real last page, the
        server re-serves that same last page instead of going empty --
        "stop on empty" alone would loop forever."""
        f = BestwineauctionsFetcher()
        page1 = "".join(_card_html(i, "Closed 01 Jan 2020") for i in (1, 2))
        page2 = "".join(_card_html(i, "Closed 01 Jan 2019") for i in (3, 4))

        def fake_render(url, selector, timeout=15000, settle_js=None, attempts=2):
            n = int(re.search(r"page=(\d+)", url).group(1))
            return page1 if n == 1 else page2

        f._render = fake_render
        cards = list(f._iter_category_cards("128", "bordeaux-red", None))
        self.assertEqual([c["lot_id"] for c in cards], ["1", "2", "3", "4"])


if __name__ == "__main__":
    unittest.main()
