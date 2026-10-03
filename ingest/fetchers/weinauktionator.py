"""Fetcher for Weinauktionator result XLSX files.

- discover: parse ``/de/info/results`` for the numbered XLSX result links.
- fetch: download the XLSX bytes (the actual parsing is a separate step).
"""
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.weinauktionator.de"

XLSX_LINK = re.compile(
    r'/de/info/results/xlsx/(\d+)/weinauktionator_results_\d+\.xlsx')


class WeinauktionatorFetcher:
    provider = "weinauktionator"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def discover(self, session):
        html = session.get(f"{self.base_url}/de/info/results").text
        refs = []
        seen = set()
        for match in XLSX_LINK.finditer(html):
            number = match.group(1)
            if number in seen:
                continue
            seen.add(number)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=number,
                url=self.base_url + match.group(0),
                title=f"Weinauktionator {number}",
            ))
        return refs

    def fetch(self, session, ref):
        resp = session.get(ref.url)
        resp.raise_for_status()
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            content=resp.content,
            filename=f"weinauktionator_results_{ref.auction_id}.xlsx",
        )
