"""Fetcher for Hart Davis Hart auction result PDFs.

- discover: parse ``/auction-archives/`` for ``{YYMM}_AuctionResults*.pdf``
  links and use the sale number (e.g. ``2609``) as the auction id.
- fetch: download the result PDF bytes (the actual parsing is a separate step).
"""
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://hdhauctions.com"

RESULTS_LINK = re.compile(
    r'https://hdhauctions\.com/wp-content/uploads/\d{4}/\d{2}/'
    r'(\d{4})_AuctionResults[A-Za-z_]*\.pdf')


class HdhFetcher:
    provider = "hdh"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(f"{self.base_url}/auction-archives/").text
        refs = []
        seen = set()
        for match in RESULTS_LINK.finditer(html):
            sale = match.group(1)
            if sale in seen:
                continue
            seen.add(sale)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=sale,
                url=match.group(0),
                title=f"HDH {sale}",
            ))
        return refs

    def fetch(self, session, ref):
        resp = session.get(ref.url)
        resp.raise_for_status()
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            content=resp.content,
            filename=f"{ref.auction_id}_results.pdf",
        )
