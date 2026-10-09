"""Fetcher for Sothebys auction results (Turnstile + login required).

- auth: run the camoufox login flow (solves Cloudflare Turnstile) and put the
  resulting ``globid`` cookie into the session.
- discover: parse ``/en/results`` for ``/en/buy/auction/{year}/{slug}`` links.
- fetch: read the auction id (UUID) from the Next.js ``__NEXT_DATA__`` Apollo
  cache, then query the GraphQL API for the lots incl. the hammer
  (``bidState.bidAsk``) and estimates.
"""
import json
import re

from ..models import AuctionRef, FetchResult
from ..sothebys_auth import login as sothebys_login

BASE_URL = "https://www.sothebys.com"
GRAPHQL_URL = "https://clientapi.prod.sothelabs.com/graphql"

CATEGORY_IDS = [
    "00000164-609a-d1db-a5e6-e9fffcc80000",  # Wine
    "0000017e-b9db-d1d4-a9fe-bdfb5bbc0000",  # Whisky & Spirits
]

LOTS_QUERY = (
    '{ auction(id: "%s") {'
    ' lotCardsConnection(filter: "ALL", limit: 1000, offset: %d) {'
    '  lots {'
    '   title'
    '   lotNumber { ... on VisibleLotNumber { lotDisplayNumber } }'
    '   bidState { bidAsk }'
    '   estimateV2 { ... on LowHighEstimateV2 { lowEstimate { amount }'
    '    highEstimate { amount } } }'
    '   auction { currency locationV2 { name } sapSaleNumber state }'
    '  }'
    '  totalCount'
    ' }'
    ' }'
    '}')


class SothebysFetcher:
    provider = "sothebys"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def auth(self, session, env):
        user = env.get("SOTHEBYS_USER")
        password = env.get("SOTHEBYS_PWD")
        if not user or not password:
            return False
        headless = env.get("SOTHEBYS_HEADLESS", "1") != "0"
        globid = sothebys_login(user, password, headless=headless)
        if not globid:
            return False
        session.cookies.set("globid", globid, domain=".sothebys.com")
        return True

    def discover(self, session):
        refs = []
        seen = set()
        for category_id in CATEGORY_IDS:
            url = (f"{self.base_url}/en/results"
                   f"?from=&to=&f2={category_id}&q=")
            html = session.get(url).text
            for match in re.finditer(r'/en/buy/auction/(\d{4})/([a-z0-9\-]+)',
                                     html):
                year, slug = match.group(1), match.group(2)
                if slug in seen:
                    continue
                seen.add(slug)
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=slug,
                    url=f"{self.base_url}/en/buy/auction/{year}/{slug}",
                ))
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        auction = self._extract_auction(html)
        lots = self._graphql_lots(session, auction.get("auction_id"))
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"auction": auction, "lots": lots},
        )

    @staticmethod
    def _extract_auction(html):
        apollo = _apollo_cache(html)
        for key, value in apollo.items():
            if key.startswith("Auction:") and value.get("auctionId"):
                dates = value.get("dates") or {}
                return {
                    "auction_id": value.get("auctionId"),
                    "title": value.get("title"),
                    "dates": dates.get("closed") or dates.get("acceptsBids"),
                    "currency": value.get("currencyV2"),
                    "location": (value.get("locationV2") or {}).get("name"),
                }
        return {}

    @staticmethod
    def _graphql_lots(session, auction_id):
        if not auction_id:
            return []
        lots = []
        offset = 0
        while True:
            query = LOTS_QUERY % (auction_id, offset)
            resp = session.post(
                GRAPHQL_URL,
                json={"query": query},
                headers={"Content-Type": "application/json"},
            )
            data = resp.json().get("data", {})
            connection = ((data.get("auction") or {})
                          .get("lotCardsConnection") or {})
            page_lots = connection.get("lots") or []
            for lot in page_lots:
                estimate = lot.get("estimateV2") or {}
                low = (estimate.get("lowEstimate") or {}).get("amount")
                high = (estimate.get("highEstimate") or {}).get("amount")
                bid_state = lot.get("bidState") or {}
                bid_ask = bid_state.get("bidAsk")
                auction = lot.get("auction") or {}
                lots.append({
                    "lot_number": (lot.get("lotNumber") or {})
                    .get("lotDisplayNumber"),
                    "title": lot.get("title"),
                    "estimate_low": low,
                    "estimate_high": high,
                    "hammer_price": bid_ask,
                    "final_price": _final_price(bid_ask),
                    "sold": 1 if bid_ask else 0,
                    "currency": auction.get("currency"),
                })
            offset += len(page_lots)
            total = connection.get("totalCount") or 0
            if not page_lots or offset >= total:
                break
        return lots


def _final_price(hammer):
    """Sothebys buyer's premium 24% + overhead 1% on top of the hammer."""
    if hammer is None:
        return None
    try:
        return round(float(hammer) * 1.25, 2)
    except (ValueError, TypeError):
        return None


def _apollo_cache(html):
    match = re.search(
        r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    if not match:
        return {}
    try:
        doc = json.loads(match.group(1))
    except (ValueError, TypeError):
        return {}
    return (doc.get("props", {}).get("pageProps", {})
            .get("apolloCache", {}))
