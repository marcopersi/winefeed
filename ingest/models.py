"""Data models for the ingest module."""
from dataclasses import dataclass, field


@dataclass
class AuctionRef:
    """A single auction discovered at a house, before fetching its lots."""
    provider: str
    auction_id: str
    url: str = ""
    title: str = ""
    date: str = ""
    etag: str = ""


@dataclass
class FetchResult:
    """Result of fetching one auction: the raw data plus provenance."""
    provider: str
    auction_id: str
    data: dict = field(default_factory=dict)
