"""Fetcher for iDealwine's public 'cote' JSON API.

iDealwine has no per-auction list; it exposes a continuous price database
("cote") per wine. Discovery enumerates all wines of the three regions, then
fetch loads the per-wine rating history.

- discover: ``/api/v2/shop/vintage-ratings-by-product-for-region-d-t-os/by-region/{region}``
  (paginated via ``hydra:member`` / ``hydra:totalItems``).
- fetch: ``/api/v2/shop/product-vintage-rating-info/{productId}-{vintage}``.
"""
from ..models import AuctionRef, FetchResult

REGIONS = ["bordeaux", "bourgogne", "rhone"]


class IdealwineFetcher:
    provider = "idealwine"

    def __init__(self, base_url="https://www.idealwine.com/api/v2/shop"):
        self.base_url = base_url.rstrip("/")

    def _headers(self):
        return {"accept": "application/json"}

    def discover(self, session):
        refs = []
        for region in REGIONS:
            page = 1
            while True:
                url = (f"{self.base_url}/vintage-ratings-by-product-for-"
                       f"region-d-t-os/by-region/{region}"
                       f"?page={page}&itemsPerPage=100")
                body = session.get(url, headers=self._headers()).json()
                members = body.get("hydra:member") or []
                for m in members:
                    pid = m.get("productId")
                    year = m.get("year")
                    if pid is None or year is None:
                        continue
                    code = f"{pid}-{year}"
                    refs.append(AuctionRef(
                        provider=self.provider,
                        auction_id=code,
                        url=f"{self.base_url}/product-vintage-rating-info/{code}",
                        title=m.get("wineName") or "",
                    ))
                total = body.get("hydra:totalItems")
                if not members or (total and len(refs) >= total):
                    break
                page += 1
        return refs

    def fetch(self, session, ref):
        body = session.get(ref.url, headers=self._headers()).json()
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data=body,
        )
