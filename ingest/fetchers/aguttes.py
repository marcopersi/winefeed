"""Fetcher for Aguttes' "Grands Vins & Spiritueux" department (Next.js
Pages-Router site, ``__NEXT_DATA__`` embedded JSON -- no bot protection
encountered via plain curl_cffi, confirmed on ~15 manual requests).

- discover: pages through ``/ventes/ventes-passees?page=N`` (own
  robots.txt disallows ``/lots?department=``, ``/api/``, ``/_next/`` --
  NOT this path), reading each sale's structured ``department_uuid``
  straight from the listing's own dehydrated react-query cache
  (``dehydratedState.queries[0].state.data``) rather than guessing a URL
  slug: a catalogue URL built from the sale's bare uuid
  (``/catalogue/{uuid}``) 308-redirects to the real slugged URL,
  confirmed real, so no slug field is ever needed. A ``?department=``
  query param on this listing path does NOT filter server-side (confirmed
  real: byte-identical response with or without it) -- filtering is done
  here, client-side, after reading each page's own JSON.
- fetch: the catalogue page's own ``__NEXT_DATA__`` carries the auction
  object (``premiums`` -- a tiered buyer's-premium schedule, HT/excl. VAT
  -- and ``tax_rate``) plus a paginated ``auctionLots`` block (``?page=N``,
  ``count``/``limit`` giving the same "trust the total" completeness
  check as drouot_template.py). Confirmed real (Aguttes' own English AND
  French ``terms_and_conditions`` text, both quoted explicitly, e.g. EN:
  "For sales in the ... Wines & Spirits [department]: 21% excl. taxes +
  VAT at the current rate, i.e. 25.2% incl. taxes"): the premium's quoted
  percentage is HT (excl. VAT), with VAT charged separately ON TOP of the
  premium to reach the TTC total -- the OPPOSITE convention from the 4
  Drouot-template houses (whose quoted "NN% TTC" already includes VAT).
  ``premium_rate`` (HT) and the auction's ``vat_rate`` therefore travel
  separately for the loader (``load_aguttes`` in ``data/build_db.py``) to
  compose, rather than one all-inclusive rate. The premium schedule can
  step DOWN above a threshold (a second, lower tier observed on some
  non-wine sales), so the applicable rate is resolved PER LOT against its
  own hammer price, not once per auction.
- A second, older catalogue-page shape exists (confirmed real: 1 of 51
  wine sales sampled Nov 2026, sale_no 170340): ``auction``/``auctionLots``
  are both null, and ``drouotVente``/``drouotLots`` carry the sale instead
  -- a legacy mirror of Aguttes' own Drouot-gateway-routed sales, never
  migrated into the native Artisio schema. This shape has NO pagination
  (every lot is already in ``drouotLots`` on page 1) and a DIFFERENT price
  basis: ``adjudication_price_with_fees`` is already TTC (fee- and
  VAT-inclusive, like the 2 Drouot-template houses' "sans frais" figure's
  opposite number) -- confirmed real: "0.00" (not null/absent) is how an
  unsold lot's price reads here, so ``sold`` is ``price > 0``, not merely
  "price is not None".
"""
import json
import re

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.aguttes.com"
LISTING_PATH = "/ventes/ventes-passees"
# Aguttes' own structured department id for "Grands Vins & Spiritueux"
# (confirmed stable across every wine sale checked, both current
# V{YY}VIN{NN}-coded sales and older numeric-only sale_no legacy ones).
WINE_DEPARTMENT_UUID = "e321d3cf-ae9d-43a2-9959-7e035e52eeda"

_NEXT_DATA = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL)

_VINTAGE = re.compile(r"\b(1[5-9]\d{2}|20\d{2})\b")
_QUANTITY = re.compile(
    r"^(\d+)\s*(?:bouteilles?|blles?|b\.?|magnums?|mags?|dmg|"
    r"j[ée]ro(?:boams?)?|jh|demis?|double\s*mags?|"
    r"imp(?:[ée]riales?)?)\b", re.I)


class MalformedResponse(RuntimeError):
    """Expected __NEXT_DATA__/auctionLots structure is missing."""


class ReconciliationMismatch(RuntimeError):
    """Fetched lot count does not match the catalogue's own advertised total."""


def _next_data(html):
    match = _NEXT_DATA.search(html)
    return json.loads(match.group(1)) if match else None


def _strip_html(text):
    return BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)


def _to_float(value):
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _localized(value):
    value = value or {}
    return value.get("fr") or value.get("en")


def _premium_rate_ht(premiums, hammer_price):
    """Pick the tiered buyer's-premium rate (HT) applying to one lot's own
    hammer price -- see module docstring on why this is per-lot, not
    per-auction. Returns None if no tier's ``amount_over`` threshold is at
    or below the hammer price (e.g. an empty/malformed schedule, or one
    that doesn't cover low-value lots) -- the caller treats that as a
    real problem on a sold lot, not a silent gap."""
    if not premiums or hammer_price is None:
        return None
    rate = None
    for tier in sorted(premiums, key=lambda t: t.get("amount_over") or 0):
        if hammer_price >= (tier.get("amount_over") or 0):
            rate = _to_float(tier.get("percent"))
    return round(rate / 100, 4) if rate is not None else None


def _extract_vintage_and_quantity(wine_text):
    # Distinct years, not raw match count -- a grouped lot mentioning the
    # SAME year twice (two sub-lots from the same vintage) is not
    # actually ambiguous.
    vintage_years = set(_VINTAGE.findall(wine_text))
    vintage = next(iter(vintage_years)) if len(vintage_years) == 1 else None
    quantity_match = _QUANTITY.match(wine_text)
    quantity = int(quantity_match.group(1)) if quantity_match else None
    return vintage, quantity


class AguttesFetcher:
    provider = "aguttes"

    def discover(self, session):
        refs = []
        page = 1
        total_pages = 1
        while page <= total_pages:
            html = session.get(f"{BASE_URL}{LISTING_PATH}",
                               params={"page": page}).text
            payload = _next_data(html)
            if payload is None:
                raise MalformedResponse(
                    f"aguttes: no __NEXT_DATA__ on {LISTING_PATH} "
                    f"(page {page})")
            cache = (payload["props"]["pageProps"]["dehydratedState"]
                     ["queries"][0]["state"]["data"])
            total_pages = cache.get("total_pages") or total_pages
            for sale in cache.get("results", []):
                if sale.get("department_uuid") != WINE_DEPARTMENT_UUID:
                    continue
                uuid = sale["uuid"]
                dates = sale.get("dates") or []
                date = (dates[0].get("start_date") if dates
                       else sale.get("start_date")) or ""
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=uuid,
                    url=f"{BASE_URL}/catalogue/{uuid}",
                    title=_localized(sale.get("title")) or "",
                    date=date[:10] if date else "",
                ))
            page += 1
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url, params={"page": 1}).text
        payload = _next_data(html)
        if payload is None:
            raise MalformedResponse(
                f"{self.provider}/{ref.auction_id}: no __NEXT_DATA__ on "
                f"{ref.url}")
        props = payload["props"]["pageProps"]
        if props.get("auction"):
            return self._fetch_artisio(session, ref, props)
        if props.get("drouotVente") and props.get("drouotLots") is not None:
            return self._fetch_drouot_gateway(ref, props)
        raise MalformedResponse(
            f"{self.provider}/{ref.auction_id}: catalogue page has "
            "neither 'auction'/'auctionLots' nor 'drouotVente'/"
            "'drouotLots'")

    def _fetch_artisio(self, session, ref, first_page_props):
        auction_meta = first_page_props.get("auction") or {}
        lots_raw = []
        page = 1
        props = first_page_props
        while True:
            auction_lots = props.get("auctionLots") or {}
            count, limit = auction_lots.get("count"), auction_lots.get("limit")
            if count is None or limit is None:
                raise MalformedResponse(
                    f"{self.provider}/{ref.auction_id}: auctionLots "
                    "missing count/limit")
            results = auction_lots.get("results") or []
            lots_raw.extend(results)
            if not results or len(lots_raw) >= count:
                if len(lots_raw) != count:
                    raise ReconciliationMismatch(
                        f"{self.provider}/{ref.auction_id}: expected "
                        f"{count} lots, got {len(lots_raw)}")
                break
            page += 1
            html = session.get(ref.url, params={"page": page}).text
            payload = _next_data(html)
            if payload is None:
                raise MalformedResponse(
                    f"{self.provider}/{ref.auction_id}: no __NEXT_DATA__ "
                    f"on {ref.url} (page {page})")
            props = payload["props"]["pageProps"]

        premiums = auction_meta.get("premiums") or []
        tax_rate = auction_meta.get("tax_rate")
        vat_rate = round(float(tax_rate) / 100, 4) if tax_rate is not None \
            else None
        dates = auction_meta.get("dates") or []
        date = (dates[0].get("start_date") if dates else None) or ref.date
        title = _localized(auction_meta.get("title")) or ref.title

        lots = [self._map_lot(raw, premiums) for raw in lots_raw]
        for lot in lots:
            if lot["sold"] and lot["premium_rate"] is None:
                # A sold lot's own hammer price fell outside every tier
                # in `premiums` (or the schedule was empty/malformed) --
                # confirmed real tiered schedules always cover 0 upward,
                # so this signals missing/bad fee data worth a human
                # look, not a lot to silently archive without a price.
                raise RuntimeError(
                    f"{self.provider}/{ref.auction_id}: lot "
                    f"{lot['lot_no']} is sold but no premium tier "
                    f"applies to hammer_price={lot['hammer_price']!r} "
                    f"(premiums={premiums!r})")

        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {
                    "id": ref.auction_id, "name": title,
                    "date": date[:10] if date else None,
                    "currency": "EUR", "vat_rate": vat_rate,
                    "sale_no": auction_meta.get("sale_no"),
                    "price_basis": "HAMMER",
                },
                "lots": lots,
            },
        )

    def _fetch_drouot_gateway(self, ref, props):
        vente = props["drouotVente"]
        lots_raw = props["drouotLots"] or []
        title = _localized({"fr": vente.get("title_fr"),
                            "en": vente.get("title_en")}) or ref.title
        date = vente.get("date") or ref.date
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {
                    "id": ref.auction_id, "name": title,
                    "date": date[:10] if date else None,
                    "currency": "EUR",
                    "sale_no": str(vente.get("sale_id") or ""),
                    "price_basis": "HAMMER_PLUS_BUYERS_PREMIUM",
                },
                "lots": [self._map_drouot_gateway_lot(raw)
                        for raw in lots_raw],
            },
        )

    @staticmethod
    def _map_lot(raw, premiums):
        sold = raw.get("status") == "sold"
        hammer_price = _to_float(raw.get("hammer_price")) if sold else None
        fields = _localized(raw.get("dynamic_fields")) or {}
        wine_text = _strip_html(fields.get("description")
                                or fields.get("title"))
        vintage, quantity = _extract_vintage_and_quantity(wine_text)

        return {
            "lot_no": raw.get("lot_no"), "wine": wine_text,
            "vintage": vintage, "quantity": quantity,
            "estimate_low": _to_float(raw.get("low")),
            "estimate_high": _to_float(raw.get("high")),
            "hammer_price": hammer_price, "sold": sold,
            "premium_rate": _premium_rate_ht(premiums, hammer_price),
        }

    @staticmethod
    def _map_drouot_gateway_lot(raw):
        price = _to_float(raw.get("adjudication_price_with_fees"))
        # Confirmed real (sale_no 170340): an unsold lot's price reads
        # literally "0.00" here, not null/absent -- this is NOT the same
        # "price present but zero" shape as any other provider, so it
        # must be checked explicitly rather than treating any non-null
        # price as sold.
        sold = price is not None and price > 0
        wine_text = _strip_html(raw.get("title_fr") or raw.get("title_en"))
        vintage, quantity = _extract_vintage_and_quantity(wine_text)
        lot_no = str(raw.get("number") or "")
        if raw.get("number_extension"):
            lot_no += str(raw["number_extension"])

        return {
            "lot_no": lot_no, "wine": wine_text,
            "vintage": vintage, "quantity": quantity,
            "estimate_low": _to_float(raw.get("low_estimate")),
            "estimate_high": _to_float(raw.get("high_estimate")),
            "realised_price": price if sold else None, "sold": sold,
        }
