"""Fetcher for Dorotheum auction results.

Dorotheum is server-side rendered behind a Cloudflare challenge; the session
must use browser impersonation (``curl_cffi``) so the challenge is solved
automatically.

- discover: parse ``/de/auktionsergebnisse/`` for ``/de/a/{id}/`` links.
- fetch: load the auction page and extract the inline ``var lots = {...}``
  JSON (keyed by lot uid). Each lot carries ``titel``, ``postennummer``,
  ``preisFloat`` (hammer), ``preis1`` ("Erzielter Preis"), ``preis2``
  ("Schätzwert"), ``preis3`` ("Startpreis") and ``beschreibung``.
"""
import re
from json.decoder import JSONDecoder

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.dorotheum.com"


class DorotheumFetcher:
    provider = "dorotheum"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(
            f"{self.base_url}/de/auktionsergebnisse/").text
        refs = []
        seen = set()
        for match in re.finditer(r'/de/a/(\d+)/', html):
            aid = match.group(1)
            if aid in seen:
                continue
            seen.add(aid)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=aid,
                url=f"{self.base_url}/de/a/{aid}/",
            ))
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        raw = self._extract_lots(html)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"auction": {"id": ref.auction_id, "name": None,
                              "date": None},
                  "lots": [self._map_lot(lot) for lot in raw.values()]},
        )

    @staticmethod
    def _extract_lots(html):
        marker = html.find("var lots = ")
        if marker == -1:
            return {}
        start = html.find("{", marker)
        return JSONDecoder().raw_decode(html[start:])[0]

    @staticmethod
    def _map_lot(lot):
        price = lot.get("preisFloat")
        return {
            "lot_nr": lot.get("postennummer"),
            "name": lot.get("titel"),
            "estimate": _parse_price(lot.get("preis2")),
            "realized_price": price,
            "sold": 1 if price else 0,
            "currency": "EUR",
            "description": lot.get("beschreibung"),
        }


def _parse_price(text):
    """European number format: 'EUR 1.500,-' -> 1500.0, 'EUR 800,-' -> 800.0."""
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "",
                    str(text).replace(".", "").replace(",", "."))
    return float(digits) if digits else None
