"""Fetcher for Winefields (Auction Mobility) auction results.

- discover: follow the WordPress ``/auction-highlight/`` posts on the overview
  page to the underlying ``auctions.winefields.com/auctions/{id}/{slug}`` URLs.
- fetch: load the auction page with ``?limit=<large>`` so all lots are rendered
  server-side, then extract the inline ``lots.result_page`` JSON plus the
  auction meta (location, currency, buyer's premium).
"""
import json
import re
from json.decoder import JSONDecoder

from ..models import AuctionRef, FetchResult

OVERVIEW_URL = "https://www.winefields.com/auctions/"

LOT_ANCHOR = '"lots":{"result_page":['

META_FIELDS = (
    "location_name", "currency_code", "default_buyers_premium",
    "minimum_buyers_premium", "percentage_bidding", "lot_count",
    "sold_lot_count", "auction_code",
)


class WinefieldsFetcher:
    provider = "winefields"

    def __init__(self, overview_url=OVERVIEW_URL):
        self.overview_url = overview_url

    def discover(self, session):
        html = session.get(self.overview_url).text
        highlights = sorted(set(re.findall(
            r'href="(https://www\.winefields\.com/auction-highlight/[^"]+)"',
            html)))
        refs = []
        seen = set()
        for highlight_url in highlights:
            post_html = session.get(highlight_url).text
            match = re.search(
                r'https://auctions\.winefields\.com/auctions/'
                r'([A-Z0-9\-]+)/[a-z0-9\-]+', post_html)
            if not match:
                continue
            auction_id = match.group(1)
            if auction_id in seen:
                continue
            seen.add(auction_id)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=auction_id,
                url=match.group(0),
            ))
        return refs

    def fetch(self, session, ref):
        html = session.get(f"{ref.url}?limit=9999").text
        lots = self._extract_lots(html)
        meta = self._extract_meta(html)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider,
                  "auction_id": ref.auction_id,
                  "auction": meta,
                  "lots": lots},
        )

    @staticmethod
    def _extract_lots(html):
        anchor = html.find(LOT_ANCHOR)
        if anchor == -1:
            return []
        start = html.find("[", anchor)
        array, _ = JSONDecoder().raw_decode(html[start:])
        return array

    @staticmethod
    def _extract_meta(html):
        meta = {}
        for field in META_FIELDS:
            match = re.search(r'"' + field + r'":("[^"]*"|null|[0-9.]+)',
                              html)
            if match:
                meta[field] = json.loads(match.group(1))
        return meta
