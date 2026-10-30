"""Fetcher for the shared 'weinauktion' platform (Steinfels, Weinboerse).

Both houses run the same auction software:

- discover: ``GET /api/auctions`` -> list of auctions, each with one or more
  catalogs whose ``id`` is the ``cat_id`` used to page through lots.
- fetch: ``GET /api/lots?cat_id={id}&...&$page={i}&$maxpagesize=50``, paginated
  until ``$totalPages`` is reached.
"""
import re

from ..models import AuctionRef, FetchResult

API_VERSION = "1.14"
PAGE_SIZE = 50


class WeinauktionFetcher:
    def __init__(self, provider, base_url):
        self.provider = provider
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        return {
            "accept": "text/json",
            "x-api-version": API_VERSION,
        }

    def discover(self, session):
        refs = []
        url = f"{self.base_url}/api/auctions"
        auctions = session.get(url, headers=self._headers()).json()
        if not isinstance(auctions, list):
            auctions = []
        for auction in auctions:
            for catalog in auction.get("catalogs", []):
                cat_id = catalog.get("id")
                if cat_id is None:
                    continue
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=str(cat_id),
                    url=f"{self.base_url}/api/lots?cat_id={cat_id}",
                    title=auction.get("title") or catalog.get("title") or "",
                    date=(auction.get("startDate") or "")[:10],
                ))
        return refs

    def fetch(self, session, ref):
        lots = []
        meta = {}
        page = 1
        total_pages = 1
        while page <= total_pages:
            url = (f"{self.base_url}/api/lots"
                   f"?cat_id={ref.auction_id}"
                   f"&my=false&s=&consignments_only=false"
                   f"&$sortby=lot_number&$sortdir=asc"
                   f"&$page={page}&$maxpagesize={PAGE_SIZE}")
            body = session.get(url, headers=self._headers()).json()
            lots.extend(body.get("items", []))
            total_pages = int(body.get("$totalPages") or 1)
            if page == 1:
                meta = self._meta(body)
            page += 1

        currency = meta.get("currency")
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {
                    "id": ref.auction_id,
                    "name": meta.get("title") or ref.title,
                    "date": meta.get("startDate") or ref.date,
                    "currency": currency,
                },
                "lots": [self._map_lot(lot, currency) for lot in lots],
            },
        )

    @staticmethod
    def _meta(body):
        related = body.get("@related") or {}
        auctions = related.get("auctions") or []
        catalogs = related.get("catalogs") or []
        auction = auctions[0] if auctions else {}
        catalog = catalogs[0] if catalogs else {}
        return {
            "auction_id": auction.get("id"),
            "title": auction.get("title"),
            "startDate": auction.get("startDate"),
            "endDate": auction.get("endDate"),
            "currency": auction.get("currency"),
            "terms": auction.get("additionalTermsAndConditionsText") or "",
            "catalog_id": catalog.get("id"),
            "catalog_description": catalog.get("description") or "",
        }

    @staticmethod
    def _map_lot(lot, currency):
        text = _strip_html(lot.get("shortDescription")
                            or lot.get("description") or "")
        return {
            "lot_no": lot.get("number"),
            "wine": text or None,
            "vintage": _year_in(text),
            "estimate_low": lot.get("basePrice"),
            "estimate_high": lot.get("upperBasePrice"),
            "hammer_price": lot.get("hammerPrice"),
            "sold": 1 if lot.get("state") == "sold" else 0,
            "currency": currency,
            # Preserved for a future richer re-parse (see
            # data/build_db.py's weinboerse description parser) -- the
            # flattened "wine" text above loses the structured
            # producer/quantity/OHK fields a fuller parse could recover,
            # so the raw HTML is kept rather than discarded at this layer.
            "description": lot.get("description"),
        }


def _strip_html(text):
    return re.sub(r"<[^>]+>", " ", text or "").strip()


def _year_in(text):
    match = re.search(r"\b(19|20)\d{2}\b", text or "")
    return match.group(0) if match else None
