"""Fetcher for Sothebys auction results (Turnstile + login required).

- auth: run the camoufox login flow (solves Cloudflare Turnstile) and put the
  resulting ``globid`` cookie into the session.
- discover: parse ``/en/results`` for ``/en/buy/auction/{year}/{slug}`` links.
- fetch: load the auction page and extract the ``LotCard`` entries from the
  Next.js ``__NEXT_DATA__`` Apollo cache (title, lot number, currency,
  location, sale number, state).
"""
import json
import re

from ..models import AuctionRef, FetchResult
from ..sothebys_auth import login as sothebys_login

BASE_URL = "https://www.sothebys.com"


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
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider,
                  "auction_id": ref.auction_id,
                  "lots": self._extract_lots(html)},
        )

    @staticmethod
    def _extract_lots(html):
        match = re.search(
            r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        if not match:
            return []
        try:
            doc = json.loads(match.group(1))
        except (ValueError, TypeError):
            return []
        apollo = (doc.get("props", {}).get("pageProps", {})
                  .get("apolloCache", {}))
        lots = []
        for key, lot in apollo.items():
            if not key.startswith("LotCard:"):
                continue
            auction = lot.get("auction") or {}
            lot_slug = (lot.get("slug") or {}).get("lotSlug")
            auction_slug = (auction.get("slug") or {}).get("name")
            year = (auction.get("slug") or {}).get("year")
            lots.append({
                "title": lot.get("title"),
                "lot_no": (lot.get("lotNumber") or {}).get("lotDisplayNumber"),
                "currency": auction.get("currency"),
                "location": (auction.get("locationV2") or {}).get("name"),
                "sale_number": auction.get("sapSaleNumber"),
                "state": auction.get("state"),
                "estimate": lot.get("estimateV2"),
                "url": (f"{BASE_URL}/en/buy/auction/{year}/{auction_slug}/"
                        f"{lot_slug}" if lot_slug and auction_slug else None),
            })
        return lots
