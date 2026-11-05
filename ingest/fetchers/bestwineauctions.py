"""Fetcher for auction.bestwineauctions.com (Blazor Server / SignalR; the
"Auction-Experts" white-label platform, per its own footer link and CDN
path ``cdn.aeman.nl/AE_BestWineAuctions/...``).

No bot protection was found anywhere on this site (confirmed Nov 2026,
headless Chromium hits every page with no CAPTCHA/WAF). A browser is only
needed because the site renders via a live SignalR circuit -- there is no
REST/JSON endpoint behind the listings or lot pages, just server-pushed DOM
diffs -- so a plain Playwright + headless Chromium page is the right (and
simplest working) tool; camoufox is not needed here.

- discover: render ``/en/categories`` for the category list (``id`` is the
  real key -- several categories share a cosmetic slug like
  "all-regions"/"other-regions"), then render each category's
  ``/en/category/{id}/{slug}?page={n}`` listing, 1-indexed. Confirmed real
  (not the pager widget's unverified "62" label): a category can have
  hundreds of pages (category 128 alone still had 124 cards on page 100),
  and past the real last page the server does NOT return an empty page --
  it keeps re-serving the same last page over and over, so "stop on empty"
  alone never terminates. Pagination here stops when a page's first lot id
  repeats the previous page's first id (the clamp signal) as the hard
  backstop, AND -- for the regular incremental ``discover()`` only, not
  ``discover_backfill()`` -- as soon as a whole page's closed-dates are all
  older than ``cutoff_days`` (confirmed real: pages are overwhelmingly
  newest-closed-first, so once a page is entirely old there is nothing
  newer left on later pages). Without that cutoff, a monthly run would
  re-render every page of every category just to notice a handful of newly
  closed lots -- confirmed real cost: category 128 alone has 100+ pages at
  200 cards each. Only cards whose countdown already reads "Closed" are
  returned -- an open lot has no final price yet and would otherwise need
  re-rendering every run for nothing (same reasoning as Christies' own
  endDate gate, just applied one step earlier since the listing page
  already shows the status for free).
- fetch: render the lot's own ``/en/lot-details/{id}/...`` page and read the
  price panel (Current bid = hammer price), the two rate fields (Buyers
  premium / VAT over buyers premium -- read per lot, not assumed constant
  across auctions, since nothing on the site documents them as a fixed
  platform-wide policy), the lot-information table (Bottler, Level, Label,
  Volume, Appellation, ...), and the parent auction id/name from the
  breadcrumb link (``dashboard?auctionid={id}``). If the countdown element
  no longer reads "Closed" (should not happen for a ref discovered as
  closed, but the state is live) this returns None so the item is retried
  next run rather than silently stored with no price.
- Confirmed real, source-side (not a fetcher bug -- reproduced on a fresh
  Playwright render of the live page, so re-fetching cannot recover it): on
  ~0.5% of lots (42/8645 in the first production run), the site itself
  serves ``Appellation`` with embedded U+FFFD replacement characters (e.g.
  "C�te de Nuits") -- the accented bytes are already lost server-side.
  Left as-is rather than "fixed" since there's nothing to recover from.
- Currency: every lot sampled so far (Bordeaux Red category) is EUR; the
  page also renders a separate "other currencies" conversion grid
  (USD/JPY/GBP/...) next to the price panel -- that is a display
  conversion, not the lot's own currency, and is not read here. Other
  categories (whisky, cognac, ...) were not sampled, so this is treated as
  an assumption to revisit if a non-EUR lot ever surfaces downstream.
"""
import atexit
import datetime
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://auction.bestwineauctions.com"
# Generous buffer for a monthly job: a run that's late or overlaps a prior
# one by a few weeks still sees every newly closed lot.
DEFAULT_CUTOFF_DAYS = 120

_CATEGORY_RE = re.compile(r'/en/category/(\d+)/([^"/?]+)')
_LOT_ID_RE = re.compile(r'/en/lot-details/(\d+)/')
_CARD_CLOSED_RE = re.compile(r"Closed\s+(\d{1,2})\s+(\w{3})\w*\s+(\d{4})")


class BestwineauctionsFetcher:
    provider = "bestwineauctions"

    def __init__(self, cutoff_days=DEFAULT_CUTOFF_DAYS):
        self.cutoff_days = cutoff_days
        self._pw = None
        self._browser = None
        atexit.register(self.close)

    def close(self):
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:  # noqa: BLE001
                pass
            self._browser = None
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception:  # noqa: BLE001
                pass
            self._pw = None

    def _ensure_browser(self):
        if self._browser is None:
            # Lazy import: playwright is a heavy optional dependency.
            from playwright.sync_api import sync_playwright
            self._pw = sync_playwright().start()
            self._browser = self._pw.chromium.launch(headless=True)
        return self._browser

    def _render(self, url, wait_selector, timeout=30000, settle_js=None,
               attempts=2):
        """Render ``url`` in a fresh page and return its HTML, or None if
        ``wait_selector`` never appeared after ``attempts`` tries (used as
        "page has no more content" for pagination, not necessarily an
        error -- retried first since a transient slow/empty first render
        was observed live, which would otherwise look identical to a
        real end-of-pagination and silently drop a whole category).

        ``settle_js`` is an extra condition polled (via
        ``wait_for_function``) after ``wait_selector`` -- confirmed real
        case: the lot detail page's SSR shell renders its price panel
        container immediately (so ``wait_selector`` resolves right away)
        but with placeholder content ("0", empty countdown); the real
        values stream in moments later over the SignalR circuit. Category
        listing pages don't need this -- confirmed their cards already
        carry real content by the time the selector itself resolves.
        """
        browser = self._ensure_browser()
        for attempt in range(attempts):
            page = browser.new_page()
            try:
                page.goto(url, timeout=60000)
                page.wait_for_selector(wait_selector, timeout=timeout)
                if settle_js:
                    page.wait_for_function(settle_js, timeout=20000)
                return page.content()
            except Exception:  # noqa: BLE001
                if attempt + 1 >= attempts:
                    return None
            finally:
                page.close()

    def discover(self, session):
        cutoff = (datetime.date.today()
                  - datetime.timedelta(days=self.cutoff_days)
                  if self.cutoff_days else None)
        html = self._render(f"{BASE_URL}/en/categories",
                            'a[href*="/en/category/"]')
        if html is None:
            raise RuntimeError(
                "bestwineauctions: /en/categories did not render")
        categories = parse_categories(html)
        if not categories:
            raise RuntimeError(
                "bestwineauctions: no categories found on /en/categories")

        refs = []
        seen = set()
        for cat_id, slug in categories:
            for card in self._iter_category_cards(cat_id, slug, cutoff):
                if not card["closed"] or card["lot_id"] in seen:
                    continue
                seen.add(card["lot_id"])
                refs.append(AuctionRef(
                    provider=self.provider, auction_id=card["lot_id"],
                    url=card["url"], title=card["title"]))
        return refs

    def discover_backfill(self, session):
        """Unbounded ``discover()`` for a one-time full historical crawl --
        see ``data/run_bestwineauctions_backfill.py``."""
        saved = self.cutoff_days
        self.cutoff_days = None
        try:
            return self.discover(session)
        finally:
            self.cutoff_days = saved

    def _iter_category_cards(self, cat_id, slug, cutoff):
        page_num = 1
        prev_first_id = None
        while True:
            url = f"{BASE_URL}/en/category/{cat_id}/{slug}?page={page_num}"
            # _render()'s own retries (default attempts=2) distinguish a
            # transient render failure from genuine end-of-pagination
            # (empty .product.lot-card) by trying again first -- but its
            # own docstring admits that's a heuristic, not a certainty.
            # More attempts here cost nothing in the common case (a real
            # end-of-category still returns None/empty every time) and
            # meaningfully lower the odds of mistaking "the host hiccuped
            # twice in a row" for "there's no more content", which would
            # otherwise truncate discovery of this category's later pages
            # with no error raised at all.
            cat_html = self._render(url, ".product.lot-card", timeout=15000,
                                    attempts=4)
            if cat_html is None:
                return
            cards = parse_lot_cards(cat_html)
            if not cards:
                return
            if cards[0]["lot_id"] == prev_first_id:
                # Past the real last page: the server re-serves it instead
                # of going empty (confirmed real, category 128 pages
                # 100/150/200 all returned the identical page).
                return
            prev_first_id = cards[0]["lot_id"]
            yield from cards
            if cutoff is not None:
                dates = [c["closed_date"] for c in cards
                        if c["closed_date"] is not None]
                if dates and max(dates) < cutoff:
                    return
            page_num += 1

    def fetch(self, session, ref):
        html = self._render(
            ref.url, ".bwa-bidpanel",
            settle_js="() => { const el = "
                     "document.querySelector('.bwa-hero-countdown'); "
                     "return el && el.textContent.trim().length > 0; }")
        if html is None:
            raise RuntimeError(
                f"bestwineauctions/{ref.auction_id}: lot page did not "
                "render")
        lot = parse_lot_detail(html, ref)
        if lot is None:
            raise RuntimeError(
                f"bestwineauctions/{ref.auction_id}: not closed yet")
        auction = lot.pop("_auction")
        return FetchResult(
            provider=self.provider, auction_id=ref.auction_id,
            data={"auction": auction, "lots": [lot]})


def parse_categories(html):
    seen = {}
    for m in _CATEGORY_RE.finditer(html):
        cat_id, slug = m.group(1), m.group(2)
        seen.setdefault(cat_id, slug)
    return list(seen.items())


def parse_lot_cards(html):
    soup = BeautifulSoup(html, "html.parser")
    cards = []
    for card in soup.find_all("div", class_="lot-card"):
        link = card.find("a", href=lambda h: h and "/en/lot-details/" in h)
        if not link:
            continue
        href = link["href"]
        m = _LOT_ID_RE.search(href)
        if not m:
            continue
        title_el = card.find("div", class_="lot-title")
        title = title_el.get_text(strip=True) if title_el else None
        countdown_el = card.find("span", class_="lot-countdown")
        closed = bool(countdown_el
                      and "is-closed" in (countdown_el.get("class") or []))
        closed_date = (_card_closed_date(countdown_el.get_text(strip=True))
                       if countdown_el else None)
        cards.append({"lot_id": m.group(1), "url": href, "title": title,
                     "closed": closed, "closed_date": closed_date})
    return cards


def _card_closed_date(text):
    m = _CARD_CLOSED_RE.search(text or "")
    if not m:
        return None
    day, mon_abbr, year = m.groups()
    mon = _MONTHS.get(mon_abbr.lower())
    if not mon:
        return None
    try:
        return datetime.date(int(year), mon, int(day))
    except ValueError:
        return None


def parse_lot_detail(html, ref):
    soup = BeautifulSoup(html, "html.parser")

    countdown_el = soup.find(class_="bwa-hero-countdown")
    if (not countdown_el
            or countdown_el.get_text(strip=True).lower() != "closed"):
        return None

    rows = {}
    for row in soup.find_all("div", class_="bwa-row"):
        label_el = row.find("span", class_="bwa-row-label")
        value_el = row.find("span", class_="bwa-row-value")
        if label_el and value_el:
            rows[label_el.get_text(strip=True)] = value_el.get_text(
                strip=True)

    info = {}
    for li in soup.find_all("li", class_="detail-option-heading"):
        span = li.find("span")
        if not span:
            continue
        value = span.get_text(strip=True)
        label = li.get_text(strip=True)
        if value and label.endswith(value):
            label = label[: -len(value)]
        info[label.rstrip(":").strip()] = value

    h1 = soup.find("h1", class_="hero-heading")
    lot_no, title = None, None
    if h1:
        heading = h1.get_text(strip=True)
        parts = heading.split(":", 1)
        if len(parts) == 2:
            lot_no, title = parts[0].strip(), parts[1].strip()
        else:
            title = heading

    breadcrumb = soup.find(
        "a", href=lambda h: h and "dashboard?auctionid=" in h)
    auction_id, auction_name = None, None
    if breadcrumb:
        bc_m = re.search(r"auctionid=(\d+)", breadcrumb["href"])
        auction_id = bc_m.group(1) if bc_m else None
        auction_name = breadcrumb.get_text(strip=True)
    if not auction_id:
        # Confirmed real (never actually fired across the first
        # production run's 8645 lots -- checked directly): the old
        # fallback below ("auction_id or ref.auction_id") would have
        # silently keyed this lot under its OWN id as a bogus
        # single-lot "auction" if the breadcrumb markup were ever
        # missing on a partial/variant render, fragmenting
        # build_db.load_bestwineauctions's auction grouping with no
        # error. Raise instead so the caller skips (and retries next
        # run) rather than archiving a mis-grouped lot.
        raise RuntimeError(
            f"bestwineauctions/{ref.auction_id}: no auction breadcrumb "
            "found on lot page")

    current_bid_el = soup.find(id="currentBid")
    raw_bid = (_eur_amount(current_bid_el.get_text(strip=True))
              if current_bid_el else None)
    # Confirmed real (live-checked 2026-11-03): #currentBid can equal the
    # lot's own starting bid (e.g. one lot closed at its 800 EUR starting
    # bid with exactly 1 real bid recorded) -- a nonzero current bid alone
    # doesn't distinguish "one real bidder won it" from "nobody ever bid
    # and this field defaults to the opening price" (across the first
    # production run's 8645 archived lots, hammer_price was never null,
    # which is itself a signal this heuristic may not be catching
    # passed/no-bid lots at all). #totalBids (<span id="totalBids">N</span>,
    # a sibling of #currentBid) is the actual bid *count* the site itself
    # tracks -- a direct, unambiguous "did anyone bid" signal -- so it's
    # the primary source for sold status, with the old hammer-based
    # inference kept only as a fallback if the site ever omits this
    # element (observed stable so far, but not guaranteed forever).
    total_bids_el = soup.find(id="totalBids")
    total_bids = None
    if total_bids_el:
        try:
            total_bids = int(total_bids_el.get_text(strip=True))
        except ValueError:
            total_bids = None
    sold = (total_bids > 0 if total_bids is not None
           else raw_bid is not None and raw_bid > 0)
    if sold and raw_bid is None:
        # #totalBids > 0 but #currentBid didn't parse: there's no hammer
        # price to report either way, and "sold=True with hammer_price=
        # None" is a nonsensical state this schema has no anomaly flag
        # for -- fall back to not-sold, same convention as every other
        # "no final price" case below.
        sold = False
    # Same convention as every other fetcher (e.g. ackerwines.py): an
    # unsold lot's displayed bid is not a sale price, so it's not
    # archived as one.
    hammer = raw_bid if sold else None

    bp_text = rows.get("Buyers premium")
    vat_text = rows.get("VAT over buyers premium")
    bp_rate = _pct(bp_text)
    vat_rate = _pct(vat_text)
    buyer_premium = (round(hammer * bp_rate, 2)
                     if hammer is not None and bp_rate is not None else None)
    tax_amount = (round(buyer_premium * vat_rate, 2)
                  if buyer_premium is not None and vat_rate is not None
                  else None)
    total_price = None
    if hammer is not None:
        # A *missing* premium/VAT row genuinely means none applies (0);
        # a *present* row that failed to parse must not silently become
        # 0 too -- that would understate total_price instead of leaving
        # it unknown.
        premium_known = not bp_text or buyer_premium is not None
        tax_known = not vat_text or tax_amount is not None
        if premium_known and tax_known:
            total_price = hammer + (buyer_premium or 0) + (tax_amount or 0)

    start_el = soup.find(id="startTime")
    close_el = soup.find(id="closingTime")

    return {
        "lot_no": lot_no,
        "wine": title,
        "description": title,
        "producer": info.get("Bottler"),
        "appellation": info.get("Appellation"),
        "bottle_size_dl": _volume_dl(info.get("Volume")),
        "condition_text": info.get("Level") or info.get("Label"),
        "note": info.get("Extra info"),
        "estimate_low": _eur_amount(rows.get("Estimate price low")),
        "estimate_high": _eur_amount(rows.get("Estimate price high")),
        "hammer_price": hammer,
        "buyer_premium": buyer_premium,
        "tax_amount": tax_amount,
        "total_price": total_price,
        "realised_price": total_price,
        "price_basis": "HAMMER" if hammer is not None else "UNKNOWN",
        "currency": "EUR",
        "sold": sold,
        "lot_date": None,
        "source_url": ref.url,
        "_auction": {
            "id": auction_id,
            "name": auction_name,
            "date": _iso_date(close_el.get_text(strip=True)
                              if close_el else None),
            "start_date": _iso_date(start_el.get_text(strip=True)
                                    if start_el else None),
        },
    }


_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}
_CLOSING_DATE_RE = re.compile(
    r"(\w{3})\w*\s+(\d{1,2}),\s*(\d{4})")


def _iso_date(text):
    """"Jul 1, 2026  20:00" -> "2026-07-01". ``parse_date`` in build_db.py
    does not cover this month-first layout, so it's normalized here at
    the source instead."""
    if not text:
        return None
    m = _CLOSING_DATE_RE.search(text)
    if not m:
        return None
    mon = _MONTHS.get(m.group(1).lower())
    if not mon:
        return None
    return f"{m.group(3)}-{mon:02d}-{int(m.group(2)):02d}"


def _eur_amount(text):
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text)
    if not cleaned:
        return None
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "." in cleaned:
        # Confirmed real bug, caught live on this site's own pages: a
        # round-number bid renders as "1.050 €" -- a thousands dot
        # with NO decimal comma at all, not "1.050,00". Treating any
        # lone dot as a decimal point (the old behaviour) silently
        # divided every such amount by ~1000 (e.g. a real EUR2,695
        # Mouton Rothschild lot archived as hammer_price=2.695).
        # Site convention confirmed: dot groups are always exactly 3
        # digits (thousands), so any lone-dot group of other than 3
        # digits is a genuine decimal (rare on this site, but "12.5"
        # meaning 12.50 is not impossible) and is left alone.
        groups = cleaned.split(".")
        if all(len(g) == 3 for g in groups[1:]):
            cleaned = cleaned.replace(".", "")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _pct(text):
    if not text:
        return None
    m = re.search(r"([\d.,]+)", text)
    if not m:
        return None
    # A rate is never in the thousands, unlike a EUR amount -- reuse
    # _volume_amount's plain comma/dot-as-decimal parsing (no thousands
    # grouping), not _eur_amount's EUR-specific thousands-dot heuristic,
    # which would misparse e.g. "12.500%" as 12500 (-> 125.0) instead of
    # the intended 12.5 (-> 0.125).
    val = _volume_amount(m.group(1))
    return val / 100.0 if val is not None else None


def _volume_amount(text):
    """Parse a liter value with either a comma or a dot as the decimal
    separator -- no thousands grouping (unlike ``_eur_amount``, which is
    specifically for EUR amounts): a bottle's volume is never in the
    thousands, so a lone dot here is always a decimal point, never a
    thousands separator."""
    if not text:
        return None
    cleaned = re.sub(r"[^\d.,]", "", text)
    if not cleaned:
        return None
    cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _volume_dl(text):
    """Volume is given in liters with a comma decimal (e.g. "0,75") --
    bottle_size_dl stores deciliters, so this is *10, not *100. Checked
    directly: only 1/8645 archived lots has no parseable volume at all
    (a genuinely mixed-size lot, "1* 0,375 + 1* 0,750Ltr", that no single
    dl value nor a size keyword could resolve either), so a keyword
    fallback (build_db.parse_dl's "magnum"/"jeroboam"/"half" handling for
    other houses) hasn't actually been needed here -- kept as a cheap,
    strictly additive fallback in case a category this fetcher hasn't
    sampled yet ever renders Volume as a named size instead of a decimal.

    Confirmed real: this used to call ``_eur_amount`` to parse the decimal,
    but that function's thousands-dot heuristic is tuned for EUR amounts
    (any lone dot followed by exactly 3 digits is stripped as a thousands
    separator, e.g. "1.050" -> 1050). A Volume value is never in the
    thousands, and a future/unsampled category rendering a dot-decimal
    liter value such as "0.375" would hit that same heuristic ("375" is
    3 digits) and get silently mangled into 3750.0 dl -- a 1000x error --
    instead of the intended 3.75 dl. Parsed independently here with a
    plain comma-or-dot-as-decimal rule and no thousands grouping at all.
    """
    val = _volume_amount(text)
    if val is not None:
        return round(val * 10, 2)
    if not text:
        return None
    s = text.lower()
    if "magnum" in s:
        return 15.0
    if "jeroboam" in s:
        return 30.0
    if "half" in s:
        return 3.75
    return None
