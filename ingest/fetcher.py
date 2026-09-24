"""Fetcher interface.

Each house implements a fetcher with two methods:

- ``discover(session)`` -> list[AuctionRef]: enumerate currently known auctions
  (their ids/urls), without loading lots.
- ``fetch(session, ref)`` -> FetchResult: download one auction's lots and
  return them as a dict in the format the ``data/`` pipeline expects.
"""
from typing import Protocol

from .models import AuctionRef, FetchResult


class Fetcher(Protocol):
    provider: str

    def discover(self, session) -> list[AuctionRef]: ...

    def fetch(self, session, ref: AuctionRef) -> FetchResult: ...
