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
    # Provider-specific context discover() already has but fetch() cannot
    # re-derive on its own (e.g. idealwine's wine identity, read once from
    # the Algolia hit since the SSR page no longer carries it per-sale).
    meta: dict = field(default_factory=dict)


@dataclass
class FetchResult:
    """Result of fetching one auction: the raw data plus provenance.

    ``data`` holds JSON-serializable content; ``content``/``filename`` hold a
    raw binary download (XLSX/PDF) when the house exposes results as files.
    """
    provider: str
    auction_id: str
    data: dict = field(default_factory=dict)
    content: bytes = b""
    filename: str = ""
