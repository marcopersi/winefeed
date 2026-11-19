"""Shared fetcher for independent French auction houses built on Drouot's
white-label CMS template (confirmed byte-identical markup -- same CDN
asset fingerprint, same page structure -- across Crait+Müller, Vasari
Auction, Enchères Maisons-Laffitte and Art Richelieu). Each house runs on
its OWN domain with its OWN, permissive robots.txt (only ``/recherche/*``
disallowed) -- unlike drouot.com itself, whose own robots.txt disallows
exactly the lot/sale/category/past-auctions paths a central scraper would
need, which is why this fetcher targets the individual houses instead.

- discover: the past-sales listing page (its own path varies per house --
  ``results_path``) carries ``?year=N`` links covering its own full
  archive range; each year's listing gives a catalogue id + title
  (``.entry-title``), kept only when the title matches a wine/spirits
  keyword (``_WINE_WORDS``) before fetch() ever requests that catalogue's
  lot grid.
- fetch: the lot grid (``?offset=N&max=50``, cross-checked against the
  page's own "Lots X à Y sur TOTAL" count -- same failure class
  whiskyauction.py's "Showing N of TOTAL" check guards against) gives
  lot numbers and estimates, and -- when the lot sold -- a HAMMER price
  (the "Résultat ... EUR" / "Résultats sans frais" block; "sans frais" =
  without fees, confirmed directly against several of these houses' own
  terms text on real catalogue pages). The grid's own lot title is
  server-side TRUNCATED ("Résultat 400 EUR" sits right next to a title
  ending in "...", confirmed on every house checked) -- the untruncated
  title (quantity/producer/vintage/region, all still free text) only
  exists on the lot's own detail page (``/lot/{saleId}/{lotId}-{slug}``),
  so a lot-level keyword filter on the (truncated) grid text decides
  which of a possibly large MIXED catalogue's lots are worth that extra
  request -- the same two-tier card -> detail shape as
  ingest/fetchers/beschcannes.py, needed here because a single catalogue
  can mix wine lots with books, jewellery, or (confirmed real: Enchères
  Maisons-Laffitte) a 1,050-lot sale that is mostly Armagnac/Cognac.

The buyer's premium is quoted per SALE on the catalogue page itself
("Frais de vente : NN% TTC" / "...les frais et taxes suivants : NN %
TTC"), not fixed site-wide, so it travels with the auction record
(``premium_rate``) instead of a guessed static per-house number -- see
PREMIUM_POLICY in data/build_db.py, where each of these providers' rate
is the one actually read off a real sale, the same evidentiary standard
as franzwermuth's own terms PDF.
"""
import datetime
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

PAGE_SIZE = 50

# Collapses christies.py's own two-tier WINE_TITLE/AMBIGUOUS_TITLE idea
# into one list: being over-inclusive here only costs one extra GET
# (catalogue level) or one extra lot-detail fetch (lot level), and this
# project's own wine_resolution.spirits detector (data/build_wines.py)
# already resolves Armagnac/Cognac wine identities, so they stay in
# scope rather than being dropped. Word-boundaried so "vin"/"vins" never
# matches "vintage"/"Vincent"/"province", and so "vinyles" (vinyl
# records -- a real Art Richelieu catalogue title) doesn't match either.
_WINE_WORDS = re.compile(
    r"\bvins?\b|\bchampagne\b|\bspiritueux\b|\boenolog|\boenoph|"
    r"\bœnolog|\bœnoph|\bsommelier\b|\bbouteilles?\b|\bblles?\b|"
    r"\bmagnums?\b|\bj[ée]roboams?\b|\barmagnac\b|\bcognac\b|"
    r"\bmill[ée]sim", re.I)

_YEAR_LINK = re.compile(r"[?&]year=(\d{4})")
_CATALOGUE_HREF = re.compile(r"^/catalogue/(\d+)-")
_LOT_HREF = re.compile(r"/lot/(\d+)/(\d+)-")
_TOTAL_TEXT = re.compile(r"Lots\s+\d+\s*à\s*\d+\s*sur\s*"
                         r"([\d\xa0 ]+)")
# Anchored to a "frais" mention within 80 chars before the figure --
# both confirmed real phrasings ("Frais de vente : NN% TTC" / "...les
# frais et taxes suivants : NN % TTC") fit comfortably inside that
# window -- so an unrelated "NN% TTC" elsewhere on the page (e.g. a
# shipping/VAT note) can't be mistaken for the buyer's-premium rate
# (code-review finding: the earlier version matched the first "NN%
# TTC" anywhere on the page, with no anchor to the actual commission
# sentence).
_PREMIUM_RATE = re.compile(
    r"frais[^%]{0,80}?(\d{1,2}(?:[.,]\d)?)\s*%\s*TTC", re.I)
_VINTAGE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
_QUANTITY = re.compile(
    r"^(\d+)\s*(?:bouteilles?|blles?|magnums?|j[ée]roboams?|pots?)\b", re.I)

_FR_MONTHS = {
    "janvier": 1, "février": 2, "mars": 3, "avril": 4, "mai": 5,
    "juin": 6, "juillet": 7, "août": 8, "septembre": 9,
    "octobre": 10, "novembre": 11, "décembre": 12,
}
_DATE_VENTE = re.compile(
    r"(\d{1,2})\s+(" + "|".join(_FR_MONTHS) + r")\s+(\d{4})", re.I)


def _num(text):
    """Parses a French-formatted number, stripping space/NBSP/narrow-NBSP
    thousands separators (confirmed real: "sur 1\xa0050" and "4 150 EUR"
    both use these -- a plain ``\\d+`` regex silently truncates at the
    separator, reading "1\xa0050" as just "1")."""
    if text is None:
        return None
    cleaned = re.sub(r"[^\d,.]", "", text).replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _french_date(text):
    match = _DATE_VENTE.search(text or "")
    if not match:
        return None
    day, month_name, year = match.groups()
    month = _FR_MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{year}-{month:02d}-{int(day):02d}"


class DrouotTemplateFetcher:
    def __init__(self, provider, base_url, results_path):
        self.provider = provider
        self.base_url = base_url.rstrip("/")
        self.results_path = results_path

    def discover(self, session):
        listing_url = f"{self.base_url}{self.results_path}"
        html = session.get(listing_url).text
        # The bare listing page's own ``?year=N`` links cover the site's
        # full archive range (confirmed: 1970 and 2005-2026 on Art
        # Richelieu) -- read from the page rather than hardcoding a
        # year range, so a house's actual history is never guessed.
        years = sorted({int(y) for y in _YEAR_LINK.findall(html)})
        if not years:
            years = [datetime.date.today().year]

        refs = []
        seen = set()
        for year in years:
            page = session.get(listing_url, params={"year": year}).text
            soup = BeautifulSoup(page, "html.parser")
            for entry in soup.select(".calendrier.entry"):
                link = entry.select_one('a[href^="/catalogue/"]')
                if not link:
                    continue
                href = link["href"]
                match = _CATALOGUE_HREF.match(href)
                if not match or href in seen:
                    continue
                title_el = entry.select_one(".entry-title")
                title = title_el.get_text(strip=True) if title_el else ""
                if not _WINE_WORDS.search(title):
                    continue
                seen.add(href)
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=match.group(1),
                    url=f"{self.base_url}{href}",
                    title=title,
                ))
        return refs

    def fetch(self, session, ref):
        offset = 0
        cards = []
        name, date, premium_rate = ref.title, None, None
        expected_total = None
        while True:
            html = session.get(ref.url, params={
                "offset": offset, "max": PAGE_SIZE}).text
            soup = BeautifulSoup(html, "html.parser")
            if offset == 0:
                name_el = soup.select_one(".nom_vente")
                if name_el:
                    name = name_el.get_text(strip=True)
                date_el = soup.select_one(".date_vente")
                if date_el:
                    date = _french_date(date_el.get_text(strip=True))
                premium_rate = self._premium_rate(soup)
                total_match = _TOTAL_TEXT.search(soup.get_text(" "))
                if total_match:
                    expected_total = int(_num(total_match.group(1)))
            page_cards = soup.select("div.product.clearfix")
            if not page_cards:
                break
            cards.extend(page_cards)
            offset += PAGE_SIZE

        # Same failure class as whiskyauction.py's "Showing N of TOTAL"
        # check: a blocked/challenge response mid-pagination would look
        # exactly like "no more pages" otherwise, silently truncating
        # the catalogue instead of failing loud.
        if expected_total is not None and len(cards) != expected_total:
            raise RuntimeError(
                f"{self.provider}/{ref.auction_id}: expected "
                f"{expected_total} lots, got {len(cards)}")

        lots = []
        for card in cards:
            parsed = self._parse_card(card, ref.auction_id)
            if parsed is None:
                continue
            lots.append(self._fetch_detail(session, parsed))

        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {"id": ref.auction_id, "name": name,
                           "date": date, "currency": "EUR",
                           "premium_rate": premium_rate},
                "lots": lots,
            },
        )

    @staticmethod
    def _premium_rate(soup):
        match = _PREMIUM_RATE.search(soup.get_text(" "))
        if not match:
            return None
        return round(float(match.group(1).replace(",", ".")) / 100, 4)

    def _parse_card(self, card, auction_id):
        lot_link = card.select_one('a[href^="/lot/"]')
        if not lot_link:
            return None
        href_match = _LOT_HREF.search(lot_link["href"])
        if not href_match:
            return None
        _sale_id, lot_id = href_match.groups()
        desc_el = card.select_one(".product-description h2")
        grid_text = desc_el.get_text(" ", strip=True) if desc_el else ""
        # The grid's own title is truncated ("...") -- this filter only
        # decides whether the extra detail-page request is worth making,
        # not the final wine/spirits text (see _fetch_detail).
        if not _WINE_WORDS.search(grid_text):
            return None

        lotnum_el = card.select_one(".num_lot .lotnum")
        lot_no = lotnum_el.get_text(strip=True) if lotnum_el else None

        estimate_low = estimate_high = None
        estim_el = card.select_one(".estimAff4")
        if estim_el:
            parts = estim_el.get_text(" ").split("-", 1)
            if len(parts) == 2:
                estimate_low, estimate_high = _num(parts[0]), _num(parts[1])

        flash = card.select_one(".sale-flash2 nobr")
        sold = flash is not None
        hammer_price = None
        if sold:
            explication = card.select_one(".explicationResultats")
            expl_text = (explication.get_text(strip=True)
                        if explication else "")
            # The site shows this result block ONLY for lots that found
            # a buyer (confirmed: estimate-only lots within the SAME
            # catalogue never carry it) -- but it must say "sans frais"
            # (without fees, i.e. a true hammer price), not some other,
            # unexpected wording this fetcher has never seen, before the
            # figure is trusted as HAMMER.
            if "sans frais" not in expl_text.lower():
                raise RuntimeError(
                    f"{self.provider}/{auction_id}: lot {lot_id} has a "
                    f"Résultat without a confirmed 'sans frais' (hammer) "
                    f"label: {expl_text!r}")
            hammer_price = _num(flash.get_text())

        return {
            "lot_no": lot_no, "lot_id": lot_id,
            "detail_url": self.base_url + lot_link["href"],
            "grid_text": grid_text,
            "estimate_low": estimate_low, "estimate_high": estimate_high,
            "sold": sold, "hammer_price": hammer_price,
        }

    @staticmethod
    def _fetch_detail(session, parsed):
        html = session.get(parsed["detail_url"]).text
        soup = BeautifulSoup(html, "html.parser")
        h1 = soup.select_one("h1")
        title = (h1.get_text(" ", strip=True) if h1 else None) \
            or parsed["grid_text"]
        # Confirmed real on every house checked: the detail page's own
        # <h1> appends " - Lot N" and uses literal tabs between fields
        # (e.g. "1 bouteille\tChampagne BOLLINGER...\t\t2015") -- neither
        # belongs in the stored wine text.
        title = re.sub(r"\s*-\s*Lot\s+\d+\s*$", "", title)
        title = re.sub(r"\s+", " ", title).strip()

        vintage_matches = _VINTAGE.findall(title)
        vintage = vintage_matches[0] if len(vintage_matches) == 1 else None

        quantity_match = _QUANTITY.match(title)
        quantity = int(quantity_match.group(1)) if quantity_match else None

        return {
            "lot_no": parsed["lot_no"],
            "wine": title,
            "vintage": vintage,
            "quantity": quantity,
            "estimate_low": parsed["estimate_low"],
            "estimate_high": parsed["estimate_high"],
            "sold": parsed["sold"],
            "hammer_price": parsed["hammer_price"],
        }
