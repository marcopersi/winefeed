"""Fetcher for Whisky.Auction (whisky.auction) wine/champagne auctions.

Despite the site's name and whisky-focused branding, it also runs
dedicated wine/champagne sales (titles containing "Wine", e.g. "Fine &
Rare Wines") alongside its regular whisky sales, and occasionally mixes a
handful of wine lots into an otherwise whisky/charity auction (e.g.
"Cream Of The Crop Charity Auction & Wine Christmas 2021"). ``fetch``
therefore always scopes its request to the wine/champagne categories via
the site's own ``category`` filter (see ``WINE_CATEGORIES``, confirmed
against the live category-checkbox list on an auction page) -- a mixed
auction can never contribute a whisky lot this way, even though
``discover`` only pre-filters by auction TITLE for efficiency (skipping
the ~85% of auctions on this site with no wine content at all, rather
than fetching all of them).

- discover: parse ``/auctions`` (the full past-auctions archive, one
  unpaginated page) for auction ids/titles.
- fetch: scrape the server-rendered lot grid at
  ``/auctions/auction/{id}?pageIndex={n}&pageSize=90&category=<wine>``.

Confirmed empirically (2026-11-18): plain HTTP (no login, no JS
execution) returns full lot data; a passive Cloudflare bot-management
script is present but did not block a bare ``curl``, so this should work
with ``curl_cffi``'s browser impersonation like ackerwines/christies, no
camoufox needed.
"""
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://whisky.auction"

# The site's own "All Wine & Champagne" category filter value (the
# checkbox list on an auction page: id="allWineChampagnes"). Passed as
# the `category` query param on every fetch() request.
WINE_CATEGORIES = (
    "Wine - Bordeaux,Wine - Burgundy - Red,Wine - Burgundy - White,"
    "Wine - Europe - Other,Wine - France - Other,Wine - Italy,"
    "Wine - New World,Wine - Rhone,Wine - Spain,Champagne,"
    "Fortified & Dessert")

PAGE_SIZE = 90

# A lot's own class list (e.g. "lot lotItem CR Met") encodes its sale
# outcome: Met/NA ("reserve met"/"reserve not applicable", i.e. no
# reserve set) and Aftersale (sold after the auction closed in a
# separate deal) are all real sales; NotMet means the reserve price was
# never reached, so its ``data-winningbid`` is only the highest (losing)
# bid, not a real sale price -- confirmed via the site's own CSS, which
# only reveals the "Reserve Not met" label for the NotMet class.
_SOLD_CLASSES = {"Met", "NA", "Aftersale"}

# Confirmed real (live site, 8,649 wine lots sampled 2026-11-18): older
# auctions (pre-2021) often put the vintage at the END of the title
# ("Chateau Margaux 1989"), not just the start ("2001 Grands Echezeaux
# Magnum") -- so this searches anywhere, not just a leading anchor. When
# a title contains MORE than one year-like number, the vintage is left
# None rather than guessing which one is real: usually that means a
# genuinely bundled multi-vintage lot ("1987 ... & 1991 ...",
# "Assorted Mature Beaune: 1961, 1976, 1978 & 1983" -- 24/8,649 sampled
# lots), but occasionally a brand/product-line name that happens to
# contain an unrelated year-like number ("1997 Florio Targa Riserva
# 1840 Marsala Superiore") -- there is no reliable way to tell these
# apart from the title text alone, and picking the wrong one would be
# worse than leaving it unresolved. KNOWN LIMITATION: mixed_lots.py's
# classify_group has no rule for this house's "&"-joined-vintage
# convention, so a genuinely bundled lot may still be misclassified
# SINGLE downstream -- including, per senior review, a same-VINTAGE
# bundle ("Chateau A 1995 & Chateau B 1995"), where even
# classify_group's own "multiple vintages" check can't catch it (only
# one distinct year). Not fixed here: an "&"/"and"-based keyword rule
# was already evaluated and rejected as too prone to false positives
# during the #93 mixed-lot classification work on a different house's
# bundling convention.
_VINTAGE = re.compile(r"\b(1[89]\d{2}|20\d{2})\b")
# lotName3 examples seen: "75cl", "75cl / 13.5%", "6 x 75cl / 14%",
# "8 x 37.5cl" (multi-bottle lots give quantity as a "N x" prefix, not
# via the detail page's unrelated "Number of Bottles" field -- confirmed
# that field is some other site-wide stat, e.g. 10,475 for a single
# magnum lot, and must not be read as this lot's quantity).
_FORMAT = re.compile(
    r"^(?:(\d+)\s*x\s*)?(\d+(?:\.\d+)?)\s*cl(?:\s*/\s*([\d.]+)\s*%)?$",
    re.IGNORECASE)

# A title starting with one of these already names its own producer (a
# château/domaine/clos), so lotName2 there is extra classification/
# release text, not a producer -- confirmed: "2016 Chateau Cheval Blanc"
# -> lotName2 "Saint Emilion 1er Grand Cru Classe A - 100 points".
_SELF_IDENTIFYING_TITLE = re.compile(
    r"^(?:\d{4}\s+)?(?:Chateau|Château|Clos|Domaine)\b", re.IGNORECASE)
# lotName2 text containing a digit (a critic score, a release year) or
# an appellation/classification word is NOT a producer name even when
# the title above isn't self-identifying (confirmed: Burgundy vineyard-
# only titles like "2015 Musigny Grand Cru" can still have a producer
# name in lotName2 with a score suffix, e.g. "Jacques Frederic Mugnier
# - 100 Points" -- left unresolved rather than guessed, same as an
# unresolved vintage).
_NOT_PRODUCER = re.compile(r"\d|\bcru\b|\bclasse\b|\bappellation\b",
                           re.IGNORECASE)


def _to_float(text):
    if text is None:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class WhiskyAuctionFetcher:
    provider = "whiskyauction"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(f"{self.base_url}/auctions").text
        soup = BeautifulSoup(html, "html.parser")
        refs = []
        for entry in soup.select(".auctionentry"):
            link = entry.select_one('a[href^="/auctions/auction/"]')
            title_el = entry.select_one(".auctionentry-title-main")
            if not link or not title_el:
                continue
            title = title_el.get_text(strip=True)
            # Covers a dedicated Champagne/Fortified sale that doesn't
            # happen to say "wine" in its title. Not a guarantee (only
            # probing every auction's category-filtered lot count would
            # be): a title matching none of these would still be
            # silently skipped here.
            lowered = title.lower()
            if not any(k in lowered
                       for k in ("wine", "champagne", "fortified")):
                continue
            match = re.search(r"/auctions/auction/(\d+)", link["href"])
            if not match:
                continue
            end_el = entry.select_one(".auction-date-end .value")
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=match.group(1),
                url=f"{self.base_url}/auctions/auction/{match.group(1)}",
                title=title,
                date=end_el.get_text(strip=True) if end_el else "",
            ))
        return refs

    def fetch(self, session, ref):
        lots = []
        page = 0
        expected_total = None
        while True:
            resp = session.get(ref.url, params={
                "pageIndex": page, "pageSize": PAGE_SIZE,
                "category": WINE_CATEGORIES,
            })
            soup = BeautifulSoup(resp.text, "html.parser")
            if page == 0:
                expected_total = self._parse_total(soup)
            cards = soup.select(".lot.lotItem")
            if not cards:
                break
            page_lots = []
            for card in cards:
                # A page with no lots at all means "no more pages" above;
                # a page whose lots aren't finalized means something is
                # wrong with THIS fetch (e.g. a still-open auction slipped
                # past discover()'s "Past Auctions" scoping, or a
                # Cloudflare challenge page happened to still match the
                # ``.lot.lotItem`` selector) -- fail loud rather than
                # silently archive a non-final bid as a hammer price.
                status = card.get("data-auction-status")
                if status and status != "Close":
                    raise RuntimeError(
                        f"whiskyauction/{ref.auction_id}: lot "
                        f"{card.get('id')} has auction-status {status!r}, "
                        "expected 'Close'")
                page_lots.append(self._parse_lot(card))
            lots.extend(page_lots)
            page += 1
        # Cross-checks the page-by-page scrape against the site's own
        # "Showing 1 to N of TOTAL" count (confirmed real risk: a blocked/
        # challenge/error response on page 2+ would otherwise look
        # exactly like a clean "no more pages" -- `.lot.lotItem` would
        # just select nothing from it -- silently truncating the auction
        # instead of failing loud like christies.py's own reconciliation
        # check for the same class of failure).
        if expected_total and len(lots) != expected_total:
            raise RuntimeError(
                f"whiskyauction/{ref.auction_id}: expected "
                f"{expected_total} wine lots, got {len(lots)}")
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"auction": {"id": ref.auction_id, "name": ref.title,
                              "date": ref.date or None},
                  "lots": lots},
        )

    @staticmethod
    def _parse_total(soup):
        showing = soup.select_one(".detail-showing")
        if not showing:
            return None
        spans = showing.select("span")
        if not spans:
            return None
        digits = re.sub(r"\D", "", spans[-1].get_text())
        return int(digits) if digits else None

    @staticmethod
    def _parse_lot(card):
        classes = card.get("class") or []
        sold = any(c in _SOLD_CLASSES for c in classes)
        lot_id = (card.get("id") or "").removeprefix("lot_") or None

        name1 = card.select_one(".lotName1")
        name2 = card.select_one(".lotName2")
        name3 = card.select_one(".lotName3")
        title = (name1.get_text(strip=True) if name1 else None) or None
        detail = (name2.get_text(strip=True) if name2 else None) or None
        format_text = (name3.get_text(strip=True) if name3 else None) \
            or None

        # lotName2 is NOT a clean producer field in general: for a
        # Bordeaux-style name (the château already names the producer,
        # e.g. "2016 Chateau Cheval Blanc") it holds appellation/
        # classification/critic-score text instead ("Saint Emilion 1er
        # Grand Cru Classe A - 100 points"); for Burgundy (the vineyard
        # name alone doesn't identify a producer, e.g. "Richebourg Grand
        # Cru") it IS the producer ("Domaine Leroy"). Senior-review
        # finding: leaving producer unset for every lot (description-
        # only) pools DIFFERENT Burgundy producers' same-named wines
        # into one undifferentiated bucket downstream -- the self-
        # identifying-title/not-a-producer checks below extract it only
        # where that ambiguity doesn't apply, per each regex's own
        # comment, and leave it None (still folded into ``description``)
        # everywhere else rather than guess.
        producer = None
        if (detail and title and not _SELF_IDENTIFYING_TITLE.match(title)
                and not _NOT_PRODUCER.search(detail)):
            producer = detail

        vintage = None
        if title:
            matches = _VINTAGE.findall(title)
            vintage = matches[0] if len(matches) == 1 else None

        quantity, bottle_size_cl, abv = None, None, None
        if format_text:
            m = _FORMAT.match(format_text)
            if m:
                quantity = int(m.group(1)) if m.group(1) else 1
                bottle_size_cl = float(m.group(2))
                abv = float(m.group(3)) if m.group(3) else None

        end_date = card.get("data-enddate") or None
        return {
            "lot_no": lot_id,
            "wine": title,
            "producer": producer,
            "description": detail,
            "abv": abv,
            "vintage": vintage,
            "quantity": quantity,
            "bottle_size_cl": bottle_size_cl,
            "sold": sold,
            "hammer_price": _to_float(card.get("data-winningbid"))
            if sold else None,
            "lot_date": end_date.split(" ")[0] if end_date else None,
        }
