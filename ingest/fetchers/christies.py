"""Fetcher for Christie's wine auction results (server-rendered + JSON API).

- discover: parse ``/en/results`` for ``/en/auction/auction-{sale_id}#event``
  links (JSON-LD ``ItemList``).
- fetch: page through the ``lotsearch`` API for each auction until all lots
  (``total_hits_filtered``) are collected, and map them onto the
  ``load_christies`` format.

Note: ``discover`` currently returns all auctions; the wine/spirits category
filter is not yet applied (no department marker found in the results feed).
"""
import re
from json.decoder import JSONDecoder

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.christies.com"
LOTSEARCH_URL = ("https://www.christies.com/api/discoverywebsite/"
                 "auctionpages/lotsearch")
PAGE_SIZE = "84"

AUCTION_LINK = re.compile(r"/en/auction/auction-(\d+)#event")


class ChristiesFetcher:
    provider = "christies"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(f"{self.base_url}/en/results").text
        refs = []
        seen = set()
        for match in AUCTION_LINK.finditer(html):
            sale_id = match.group(1)
            if sale_id in seen:
                continue
            seen.add(sale_id)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=sale_id,
                url=f"{self.base_url}/en/auction/auction-{sale_id}",
            ))
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
            if not page_lots or total is None or len(lots) >= total:
                break
            page += 1
        if total is not None and len(lots) != total:
            raise RuntimeError(
                f"christies/{meta.get('sale_id')}: expected {total} lots, "
                f"got {len(lots)}")
        return lots


def _auction_meta(html, ref):
    meta = {"sale_id": ref.auction_id, "url": ref.url}
    marker = html.find('"sale_id"')
    if marker == -1:
        return meta
    start = html.rfind("{", 0, marker)
    try:
        obj, _ = JSONDecoder().raw_decode(html[start:])
    except ValueError:
        return meta
    meta["sale_id"] = obj.get("sale_id", ref.auction_id)
    meta["title"] = obj.get("title")
    meta["location"] = obj.get("sale_location")
    meta["sale_number"] = obj.get("sale_number")
    meta["saleroomcode"] = obj.get("sale_room_code")
    status = obj.get("auction_status") or {}
    match = re.match(r"(\d{4})-(\d{2})", status.get("start_date") or "")
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
