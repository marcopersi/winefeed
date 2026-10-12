"""Fetcher for Christie's wine auction results (server-rendered + JSON API).

- discover: parse ``/en/results`` and filter the embedded auction metadata
  (``followAnalyticsMetadata``) to the Wine & Spirits department.
- fetch: page through the ``lotsearch`` API for each auction until all lots
  (``total_hits_filtered``) are collected, and map them onto the
  ``load_christies`` format.

Note: ``discover`` only sees the current results-page window (newest auctions),
so historical wine auctions are not backfilled.
"""
import re
import time

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.christies.com"
LOTSEARCH_URL = ("https://www.christies.com/api/discoverywebsite/"
                 "auctionpages/lotsearch")
PAGE_SIZE = "84"
SITEMAP_INDEX_URL = "https://www.christies.com/LotFinder_Sitemap1.xml"

# The results feed embeds, per auction, a single-escaped JSON string
# ``followAnalyticsMetadata`` carrying the department and sale id. Filter to
# the Wine & Spirits department.
WINE_AUCTION = re.compile(
    r'\\"department\\":\\"(Wine|Spirits).*?\\"saleId\\":\\"(\d+)\\"', re.S)

# Legacy (past-sales) pages carry no department field, so the wine/spirits
# filter is a title heuristic. Word-boundary markers so "Vintage" (film
# posters) does not match "vin". Only unambiguous wine/spirits terms are used;
# ambiguous English words ("spirit", "palate", "burgundy" as a colour,
# "cellar" in a non-wine sense) are deliberately excluded to avoid false
# positives, at the cost of a few false negatives (e.g. "Signature Cellars"),
# which the ground-truth sample verification surfaces.
WINE_TITLE = re.compile(
    r"\b(wine|wines|vin|vins|champagne|bordeaux|bourgogne|whisky|whiskey)\b",
    re.I)


class ChristiesFetcher:
    provider = "christies"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(f"{self.base_url}/en/results").text
        refs = []
        seen = set()
        for match in WINE_AUCTION.finditer(html):
            sale_id = match.group(2)
            if sale_id in seen:
                continue
            seen.add(sale_id)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=sale_id,
                url=f"{self.base_url}/en/auction/auction-{sale_id}",
            ))
        return refs

    def discover_backfill(self, session, delay=0.0):
        """Sitemap index -> all past sales -> wine AuctionRefs (title heuristic).

        Each past-sale URL is loaded once to resolve the numeric ``sale_id`` and
        title; only wine/spirits auctions (title heuristic) are kept. Invalid
        meta (missing required fields) is skipped, not fatal (NFR-4).
        """
        index = session.get(SITEMAP_INDEX_URL).text
        subsites = re.findall(r"<loc>([^<]+)</loc>", index)
        past_sales = [u for u in subsites if "PastSales" in u]
        refs = []
        seen = set()
        for subsite in past_sales:
            xml = session.get(subsite).text
            for url in re.findall(r"<loc>([^<]+)</loc>", xml):
                html = session.get(url).text
                meta = _auction_meta(html, AuctionRef(self.provider, "",
                                                      url=url))
                try:
                    _validate_backfill_meta(meta)
                except RuntimeError as exc:
                    print(f"christies/backfill: {url}: {exc}, übersprungen",
                          flush=True)
                    continue
                if not _is_wine_title(meta.get("title")):
                    continue
                sale_id = meta["sale_id"]
                if sale_id in seen:
                    continue
                seen.add(sale_id)
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=sale_id,
                    url=url,
                    title=meta.get("title"),
                ))
                if delay:
                    time.sleep(delay)
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        meta = _auction_meta(html, ref)
        lots = self._all_lots(session, meta)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"auction": {
                "event_id": meta.get("sale_id"),
                "title": meta.get("title"),
                "year": meta.get("year"),
                "month": meta.get("month"),
                "landing_url": meta.get("url") or ref.url,
                "location": meta.get("location"),
            }, "lots": lots},
        )

    @staticmethod
    def _all_lots(session, meta):
        lots = []
        page = 1
        total = None
        while True:
            body = session.get(
                LOTSEARCH_URL,
                params=_lotsearch_params(meta, page),
                headers={"Accept": "application/vnd.christies.v2+json"},
            ).json()
            total = body.get("total_hits_filtered")
            page_lots = _map_lots(body.get("lots") or [])
            lots.extend(page_lots)
            if total is None:
                raise RuntimeError(
                    f"christies/{meta.get('sale_id')}: "
                    "total_hits_filtered missing")
            if not page_lots or len(lots) >= total:
                break
            page += 1
        if len(lots) != total:
            raise RuntimeError(
                f"christies/{meta.get('sale_id')}: expected {total} lots, "
                f"got {len(lots)}")
        return lots


def _auction_meta(html, ref):
    meta = {"sale_id": ref.auction_id, "url": ref.url}

    def _field(pattern, group=1):
        match = re.search(pattern, html)
        return match.group(group) if match else None

    sale_id = _field(r'"sale_id":"(\d+)"')
    if sale_id:
        meta["sale_id"] = sale_id
    meta["title"] = _field(r'"title":"([^"]+)"')
    meta["location"] = _field(r'"sale_location":"([^"]+)"')
    meta["sale_number"] = _field(r'"sale_number":"([^"]+)"')
    meta["saleroomcode"] = _field(r'"sale_room_code":"([^"]+)"')
    match = re.search(r'"start_date":"(\d{4})-(\d{2})', html)
    if match:
        meta["year"] = int(match.group(1))
        meta["month"] = int(match.group(2))
    return meta


def _lotsearch_params(meta, page):
    return {
        "language": "en",
        "pagesize": PAGE_SIZE,
        "geocountrycode": "",
        "saleid": meta.get("sale_id"),
        "salenumber": meta.get("sale_number") or "",
        "saleroomcode": meta.get("saleroomcode") or "",
        "page": str(page),
        "filterids": "",
        "searchphrase": "",
    }


def _map_lots(lots):
    return [_map_lot(lot) for lot in lots]


def _map_lot(lot):
    return {
        "lot_number": lot.get("lot_id_txt"),
        "title": lot.get("title_primary_txt"),
        "estimate_low": lot.get("estimate_low"),
        "estimate_high": lot.get("estimate_high"),
        "price_realised": lot.get("price_realised"),
        "lot_withdrawn": lot.get("lot_withdrawn"),
        "currency": _currency(lot.get("price_realised_txt")
                              or lot.get("estimate_txt")),
        "description": lot.get("title_secondary_txt"),
        "url": lot.get("url"),
    }


def _currency(text):
    match = re.match(r"^([A-Z]{3})\b", (text or "").strip())
    return match.group(1) if match else None


def _is_wine_title(title):
    return bool(WINE_TITLE.search(title or ""))


def _validate_backfill_meta(meta):
    """Hard-assert required legacy meta fields (NFR-4)."""
    problems = []
    if not re.fullmatch(r"\d+", str(meta.get("sale_id") or "")):
        problems.append("sale_id")
    if not re.fullmatch(r"\d+", str(meta.get("sale_number") or "")):
        problems.append("sale_number")
    if not re.fullmatch(r"[A-Za-z]{2,3}", str(meta.get("saleroomcode") or "")):
        problems.append("saleroomcode")
    year, month = meta.get("year"), meta.get("month")
    if not isinstance(year, int) or not 1990 <= year <= 2026:
        problems.append("year")
    if not isinstance(month, int) or not 1 <= month <= 12:
        problems.append("month")
    if problems:
        raise RuntimeError(
            f"christies/backfill: invalid meta fields {problems} "
            f"for sale_id={meta.get('sale_id')}")
