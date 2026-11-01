"""Fetcher for winebarrel.ch's auction archive (Joomla, server-rendered).

Not a classic multi-lot batch-sale house: each numbered "auction" on the
site is a single wine lot, continuously consigned and sold one at a time
(a consignment service with a seller-side commission, not a buyer's
premium -- see docs/premium-policy.md). So here, one "auction" (in the
AuctionRef/FetchResult sense) is one lot.

- discover: paginate ``/de/weinauktionen/auktionsarchiv?start={n}`` (20
  items/page, confirmed via each entry's ``data-auctionid="{id}"``
  attribute) until a page returns no ids.
- fetch: the lot's own detail page
  (``/de/weinauktionen/auktionsarchiv/auction/{id}``) carries everything
  in server-rendered HTML -- no XHR/JSON API, confirmed by inspecting the
  page's own inline scripts (only bid-placement endpoints under
  ``/fr/enchere/...`` exist on a *different* house, baghera; winebarrel
  has none of those at all).
"""
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.winebarrel.ch"
LIST_PATH = "/de/weinauktionen/auktionsarchiv"
PAGE_SIZE = 20

_AUCTION_ID = re.compile(r'data-auctionid="(\d+)"')
# Confirmed clean across 4 real pages (ids 267, 1966, 3732, 4183): the
# Joomla <title> tag is the bare wine name, with no "- SiteName" suffix
# the CMS commonly appends elsewhere. Not stripping anything here --
# there is nothing to strip.
_TITLE = re.compile(r"<title>([^<]*)</title>")
_FIELD = re.compile(r"<strong>([^<:]+):</strong>\s*([^<\n]*)")
_WEINGUT = re.compile(
    r"<strong>Weingut:</strong>\s*<a[^>]*>([^<]+)</a>")
_MAXBID = re.compile(r'id="maxbid">\s*([\d.,\']+)\s*<')
_ENDED_AT = re.compile(
    r"Auktion beendet um:</strong>\s*(\d{4}-\d{2}-\d{2})")
_LITERS = re.compile(r"(\d+(?:[.,]\d+)?)\s*l\b", re.IGNORECASE)


class WinebarrelFetcher:
    provider = "winebarrel"

    def discover(self, session):
        refs = []
        start = 0
        while True:
            resp = session.get(f"{BASE_URL}{LIST_PATH}?start={start}")
            ids = _AUCTION_ID.findall(resp.text)
            if not ids:
                break
            for aid in ids:
                refs.append(AuctionRef(
                    provider=self.provider, auction_id=aid,
                    url=f"{BASE_URL}{LIST_PATH}/auction/{aid}"))
            start += PAGE_SIZE
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {"id": ref.auction_id, "name": None, "date": None},
                "lots": [_map_lot(ref.auction_id, html)],
            },
        )


def _map_lot(auction_id, html):
    title_m = _TITLE.search(html)
    wine = title_m.group(1).strip() if title_m else None

    # First match wins for a repeated label -- confirmed real case:
    # "Region" appears twice (e.g. "Cataluña / Priorat" then the broader
    # "Cataluña"); the first occurrence is the more specific one.
    fields = {}
    for m in _FIELD.finditer(html):
        label = m.group(1).strip()
        if label not in fields:
            fields[label] = m.group(2).strip()

    weingut_m = _WEINGUT.search(html)
    maxbid_m = _MAXBID.search(html)
    ended_m = _ENDED_AT.search(html)
    liters_m = _LITERS.search(fields.get("Flaschengrösse", ""))

    hammer = None
    if maxbid_m:
        hammer = float(maxbid_m.group(1).replace("'", "").replace(",", ""))

    return {
        "lot_no": auction_id,
        "wine": wine,
        "producer": weingut_m.group(1).strip() if weingut_m else None,
        "region": fields.get("Region"),
        "quantity": fields.get("Anzahl Flaschen"),
        "bottle_size_dl": (float(liters_m.group(1).replace(",", ".")) * 10
                           if liters_m else None),
        "hammer_price": hammer,
        "sold": 1 if hammer is not None else 0,
        "auction_end": ended_m.group(1) if ended_m else None,
        "currency": "CHF",
    }
