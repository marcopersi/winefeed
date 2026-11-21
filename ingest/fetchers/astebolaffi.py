"""Fetcher for Aste Bolaffi's "Vini Rari e Pregiati" (wine & spirits)
department. Bespoke Laravel application (no Cloudflare/WAF observed,
``robots.txt`` fully permissive) -- plain curl, no login.

- discover: wine auctions occupy their OWN contiguous id block on this
  site's shared, cross-department auction-id sequence -- confirmed real
  by scanning ids 1-645 (Nov 2026): every single id from 605 through 642
  is a wine/spirits sale ("VINI"/"DISTILLATI" in its own ``<title>``),
  with ZERO gaps, while every id outside that block (574 ids checked) is
  either a different department or a dead id (302 redirect to the
  homepage). This makes a plain incrementing id-walk from ``START_ID``
  both the backfill AND the ongoing monthly discovery mechanism -- no
  separate backfill method needed, unlike christies.py. A small
  consecutive-miss tolerance (``_MAX_CONSECUTIVE_MISS``) guards against
  a future withdrawn/skipped id inside the block without scanning
  forever once the block is actually exited.
  The auction's own start/end dates are NOT in the static HTML the
  browser shows (``#start_date``/``#end_date`` spans are empty, JS-filled)
  but ARE embedded, server-rendered, in a ``<script>`` block as literal
  ``getLocationDate('YYYY-MM-DD HH:MM:SS')`` call arguments -- confirmed
  real on multiple auctions, stable since at least 2016. Only auctions
  whose own end date (or start date, for the rarer single-day sales with
  no distinct end) has already passed are discovered: confirmed real
  (ids 639-642), ids exist and already carry a title months before the
  sale even opens, with no results yet.
- fetch: the catalogue page (``/auction/{id}?page=N``, 10 lots/page,
  ``PAGE_SIZE``) server-renders each lot's free-text description, its
  starting price ("Base asta"), and -- once sold -- the HAMMER price
  ("Aggiudicato a"), directly as HTML text (no separate JSON/API).
  Buyer's-premium accounting has TWO distinct, per-LOT regimes, visibly
  marked on the very same catalogue page (confirmed real against Aste
  Bolaffi's own terms-and-conditions page, ``/cms/termini-e-condizioni``,
  AND cross-checked directly against individual lots' own markup):
  - "regime del margine" (the default -- the terms page: "Nessun
    particolare simbolo verrà usato per identificare i lotti venduti nel
    regime del margine"): a tiered, VAT-INCLUSIVE buyer's commission
    ("La commissione di acquisto ... è comprensiva di IVA"), applied
    PROGRESSIVELY (confirmed by the terms' own "sulla quota ... fino a"
    / "on the PORTION ... up to" wording): 25% up to EUR 250k, 22.5% on
    the portion 250k-500k, 20% on 500k-1M, 18% above -- the schedule for
    "tutte le altre aste" (all auctions other than classic cars/
    motorcycles or philately/numismatics, i.e. wine included). No VAT is
    added on top of this commission.
  - "regime IVA ordinaria": marked by a red Wingdings-bullet span plus a
    "Più IVA ordinaria" tooltip right next to that SAME lot's own price
    line (confirmed real: this sits on sold lots too, not just unsold
    ones). Its own ``title`` attribute spells out, IN FULL, the flat
    (non-tiered) commission rate AND the VAT rate for this lot's goods
    category, both parsed straight from that text rather than hardcoded
    (rates are read per lot, so a future change on the site is picked up
    automatically): e.g. "Commissioni d'asta al 18% ... IVA sul prezzo
    di aggiudicazione ... tutte le altre categorie 22% ... IVA al 22%
    sulle commissioni" -- i.e. VAT is charged BOTH on the hammer price
    AND on the commission, on top of the (VAT-exclusive) commission
    itself.
  Known, documented gap (same class as whiskyauction's/langtons'
  unverified historical rate -- see docs/premium-policy.md): the
  margin-scheme tier thresholds/rates are read off the CURRENT terms
  page and assumed stable back to 2016; only the ordinary-VAT regime's
  rate is verified per auction (it's quoted fresh on every lot, every
  auction).
"""
import datetime
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.astebolaffi.it"
# Confirmed real (full id 1-645 scan, Nov 2026): the wine/spirits
# department's auctions occupy ids 605 (2016-11-17) through at least 642
# (2027-05-06), contiguous, zero gaps either side of this exact block.
START_ID = 605
_MAX_CONSECUTIVE_MISS = 5
PAGE_SIZE = 10

_WINE_TITLE = re.compile(r"\bVINI?\b|\bDISTILLATI\b", re.I)
_DATE = re.compile(r"getLocationDate\('(\d{4}-\d{2}-\d{2})")
_EURO = re.compile(r"[^\d,.]")
_VINTAGE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
# Bottle-count units seen in free-text descriptions: "bts"/"bt" (plain
# bottles), "Mag" (magnum), "DMag"/"Dmag" (double magnum).
_UNIT = r"d?mags?|bts?"
_TOT_QTY = re.compile(rf"Tot\.\s*(\d+)\s*(?:{_UNIT})", re.I)
# Trailing size qualifiers can follow the unit before the closing paren
# (e.g. "(1 bt 6 Lt.)" -- a 6-litre format spelled out in litres instead
# of a named size), hence the non-greedy tail before ``\)``.
_SUB_QTY = re.compile(rf"\((\d+)\s*(?:{_UNIT})\b.*?\)", re.I)
_LOTTO_NO = re.compile(r"\d+")

# Terms & conditions (/cms/termini-e-condizioni), §7 "Commissioni d'asta
# per vendita di lotti con regime IVA del margine", "Per tutte le altre
# aste" schedule (wine is not auto/moto or philately/numismatics, the
# two named exceptions) -- applied PROGRESSIVELY per the "sulla quota"
# wording. (threshold, rate for the portion above that threshold).
_MARGIN_TIERS = [(0, 0.25), (250_000, 0.225), (500_000, 0.20),
                 (1_000_000, 0.18)]

_ORDINARY_RATE = re.compile(r"Commissioni d.asta al (\d+(?:[.,]\d+)?)\s*%")
_ORDINARY_VAT_HAMMER = re.compile(
    r"tutte le altre categorie\s*(\d+(?:[.,]\d+)?)\s*%")
_ORDINARY_VAT_PREMIUM = re.compile(
    r"IVA al (\d+(?:[.,]\d+)?)\s*%\s*sulle commissioni")


class MalformedResponse(RuntimeError):
    """Expected catalogue-page structure is missing."""


class ReconciliationMismatch(RuntimeError):
    """Fetched lot count does not match the catalogue's own pagination."""


def _num(text):
    if text is None:
        return None
    cleaned = _EURO.sub("", text).replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _pct(text):
    return float(text.replace(",", ".")) / 100


def _margin_commission(hammer_price):
    commission = 0.0
    for (threshold, rate), (next_threshold, _) in zip(
            _MARGIN_TIERS, _MARGIN_TIERS[1:] + [(float("inf"), None)]):
        if hammer_price <= threshold:
            break
        segment = min(hammer_price, next_threshold) - threshold
        commission += segment * rate
    return round(commission, 2)


def _extract_vintage_and_quantity(text):
    vintage_years = set(_VINTAGE.findall(text))
    vintage = next(iter(vintage_years)) if len(vintage_years) == 1 else None
    tot_match = _TOT_QTY.search(text)
    if tot_match:
        return vintage, int(tot_match.group(1))
    sub_matches = _SUB_QTY.findall(text)
    quantity = sum(int(q) for q in sub_matches) if sub_matches else None
    return vintage, quantity


class AsteBolaffiFetcher:
    provider = "astebolaffi"

    def discover(self, session):
        refs = []
        auction_id = START_ID
        misses = 0
        while misses < _MAX_CONSECUTIVE_MISS:
            resp = session.get(f"{BASE_URL}/it/auction/{auction_id}")
            html = resp.text
            title_match = re.search(r"<title>(.*?)</title>", html, re.S)
            title = re.sub(r"\s+", " ", title_match.group(1)).strip() \
                if title_match else ""
            if not _WINE_TITLE.search(title):
                misses += 1
                auction_id += 1
                continue
            misses = 0
            dates = _DATE.findall(html)
            end_date = dates[-1] if dates else None
            if end_date is not None and end_date <= _today():
                refs.append(AuctionRef(
                    provider=self.provider, auction_id=str(auction_id),
                    url=f"{BASE_URL}/it/auction/{auction_id}",
                    title=title, date=end_date))
            auction_id += 1
        return refs

    def fetch(self, session, ref):
        lots = []
        page = 1
        while True:
            html = session.get(ref.url, params={"page": page}).text
            soup = BeautifulSoup(html, "html.parser")
            rows = soup.select(".lot-row")
            if not rows:
                break
            for row in rows:
                lots.append(self._parse_row(row, ref.auction_id))
            if len(rows) < PAGE_SIZE:
                break
            page += 1

        if not lots:
            raise MalformedResponse(
                f"{self.provider}/{ref.auction_id}: no lot rows found "
                f"on {ref.url}")
        numbers = [lot["lot_no"] for lot in lots]
        if len(numbers) != len(set(numbers)):
            raise ReconciliationMismatch(
                f"{self.provider}/{ref.auction_id}: duplicate lot numbers "
                f"across pagination ({len(numbers)} rows, "
                f"{len(set(numbers))} distinct)")

        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {"id": ref.auction_id, "name": ref.title,
                           "date": ref.date, "currency": "EUR"},
                "lots": lots,
            },
        )

    def _parse_row(self, row, auction_id):
        lot_link = row.select_one(".asta-title a")
        lot_no_match = _LOTTO_NO.search(
            lot_link.get_text(strip=True) if lot_link else "")
        if lot_no_match is None:
            # A missing/unparseable lot number means the row's markup
            # isn't what this fetcher expects -- carrying a None lot_no
            # through would make two such rows (even across different
            # pages) look like a genuine duplicate-lot-number
            # pagination bug below, masking the real problem.
            raise MalformedResponse(
                f"{self.provider}/{auction_id}: a lot row has no "
                "parseable lot number")
        lot_no = lot_no_match.group(0)

        desc_el = row.select_one(".lot-dida")
        wine_text = desc_el.get_text(" ", strip=True) if desc_el else ""
        vintage, quantity = _extract_vintage_and_quantity(wine_text)

        price_text = row.get_text(" ", strip=True)
        euro_spans = row.select(".asta-euro")
        base_price = _num(euro_spans[0].get_text()) if euro_spans else None
        sold = "Aggiudicato a" in price_text
        hammer_price = buyer_premium = vat_on_hammer = vat_on_premium = None

        if sold:
            if len(euro_spans) < 2:
                raise MalformedResponse(
                    f"{self.provider}/{auction_id}: lot {lot_no} says "
                    "'Aggiudicato a' but has no second price figure")
            hammer_price = _num(euro_spans[1].get_text())
            tooltip = row.select_one('[data-toggle="tooltip"]')
            if tooltip is not None:
                title_attr = tooltip.get("title", "")
                rate_m = _ORDINARY_RATE.search(title_attr)
                vat_h_m = _ORDINARY_VAT_HAMMER.search(title_attr)
                vat_p_m = _ORDINARY_VAT_PREMIUM.search(title_attr)
                if not (rate_m and vat_h_m and vat_p_m):
                    raise MalformedResponse(
                        f"{self.provider}/{auction_id}: lot {lot_no} has "
                        "an ordinary-VAT tooltip this fetcher couldn't "
                        f"parse: {title_attr!r}")
                buyer_premium = round(hammer_price * _pct(rate_m.group(1)), 2)
                vat_on_hammer = round(
                    hammer_price * _pct(vat_h_m.group(1)), 2)
                vat_on_premium = round(
                    buyer_premium * _pct(vat_p_m.group(1)), 2)
            else:
                buyer_premium = _margin_commission(hammer_price)
                vat_on_hammer = 0.0
                vat_on_premium = 0.0
        elif "Base asta" not in price_text:
            raise MalformedResponse(
                f"{self.provider}/{auction_id}: lot {lot_no} has neither "
                "'Base asta' nor 'Aggiudicato a' -- unrecognized markup")

        return {
            "lot_no": lot_no, "wine": wine_text,
            "vintage": vintage, "quantity": quantity,
            "estimate_low": base_price,
            "hammer_price": hammer_price, "sold": sold,
            "buyer_premium": buyer_premium,
            "vat_on_hammer": vat_on_hammer,
            "vat_on_premium": vat_on_premium,
        }


def _today():
    return datetime.date.today().isoformat()
