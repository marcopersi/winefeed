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
        globid = sothebys_login(user, password)
        if not globid:
            return False
        session.cookies.set("globid", globid, domain=".sothebys.com")
        return True

    def discover(self, session):
        html = session.get(f"{self.base_url}/en/results").text
        refs = []
        seen = set()
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
        auction_id = self._extract_auction_id(html)
        lots = self._graphql_lots(session, auction_id)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider,
                  "auction_id": ref.auction_id,
                  "lots": lots},
        )

    @staticmethod
    def _extract_auction_id(html):
        apollo = _apollo_cache(html)
        for key, value in apollo.items():
            if key.startswith("Auction:") and value.get("auctionId"):
                return value["auctionId"]
        return None

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
                auction = lot.get("auction") or {}
                lots.append({
                    "title": lot.get("title"),
                    "lot_no": (lot.get("lotNumber") or {})
                    .get("lotDisplayNumber"),
                    "hammer": bid_state.get("bidAsk"),
                    "estimate_low": low,
                    "estimate_high": high,
                    "currency": auction.get("currency"),
                    "location": (auction.get("locationV2") or {}).get("name"),
                    "sale_number": auction.get("sapSaleNumber"),
                    "state": auction.get("state"),
                })
            offset += len(page_lots)
            total = connection.get("totalCount") or 0
            if not page_lots or offset >= total:
                break
        return lots


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
