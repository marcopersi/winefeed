"""Fetcher for iDealwine via Algolia enumeration + Next.js SSR data route.

iDealwine exposes no per-auction result feed. Adjudications (``soldAt`` +
``price``) live per wine in the "cote" (price history), reachable only through
the Next.js SSR data route of a concrete product-variant page. The cote JSON
API (``/api/v2/shop/product-vintage-rating-info/...``) returns 403 for direct
clients.

- discover: enumerate the currently offered lots via the Algolia ``prod_lots``
  index (fixed search-only key). Each lot yields a product-variant id used to
  build the SSR page slug.
- fetch: load ``/_next/data/{buildId}/{locale}/kaufen-ein-wein/{slug}.json``
  with ``x-nextjs-data: 1`` (the session must carry the ``cf_clearance``
  cookie) and return ``productVintageRatings``.

The ``build_id`` is deployment-specific and changes with every release; it is
read from ``__NEXT_DATA__`` in the site HTML.
"""
import re
import unicodedata

from ..models import AuctionRef, FetchResult

ALGOLIA_APP_ID = "QYOXXVLLKU"
ALGOLIA_API_KEY = "8319a3608b7579514df153d9c8ba64bd"
ALGOLIA_INDEX = "prod_lots"
ALGOLIA_QUERY_URL = "https://algolia.idealwine.com/1/indexes/{index}/query"
ALGOLIA_PAGE_SIZE = 1000

DEFAULT_LOCALE = "de"
NEXT_DATA_PAGE = "kaufen-ein-wein"
NEXT_DATA_HOST = "https://www.idealwine.com"


def slugify(value):
    value = unicodedata.normalize("NFKD", value)
    value = value.encode("ascii", "ignore").decode("ascii")
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def read_build_id(session, host=NEXT_DATA_HOST):
    """Read the current Next.js ``buildId`` from the site HTML."""
    html = session.get(host + "/", headers={"accept": "text/html"}).text
    match = re.search(r'"buildId":"([^"]+)"', html)
    if not match:
        raise RuntimeError("buildId not found in iDealwine homepage HTML")
    return match.group(1)


class IdealwineFetcher:
    provider = "idealwine"

    def __init__(self, build_id=None, locale=DEFAULT_LOCALE,
                 host=NEXT_DATA_HOST):
        self.build_id = build_id
        self.locale = locale
        self.host = host.rstrip("/")

    def _ensure_build_id(self, session):
        if self.build_id is None:
            self.build_id = read_build_id(session, self.host)

    def _next_data_url(self, slug):
        return (f"{self.host}/_next/data/{self.build_id}/{self.locale}/"
                f"{NEXT_DATA_PAGE}/{slug}.json")

    @staticmethod
    def _next_headers():
        return {"accept": "*/*", "x-nextjs-data": "1"}

    @staticmethod
    def _algolia_headers():
        return {
            "x-algolia-api-key": ALGOLIA_API_KEY,
            "x-algolia-application-id": ALGOLIA_APP_ID,
            "content-type": "application/json",
        }

    def discover(self, session):
        self._ensure_build_id(session)
        refs = []
        seen = set()
        page = 0
        while True:
            body = self._algolia_page(session, page)
            hits = body.get("hits") or []
            for hit in hits:
                pid = hit.get("id")
                product = hit.get("product")
                vintage = hit.get("vintage")
                name = hit.get("name") or ""
                if pid is None or product is None:
                    continue
                key = (product, vintage)
                if key in seen:
                    continue
                seen.add(key)
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=f"{product}-{vintage}",
                    url=self._next_data_url(f"{pid}-{slugify(name)}"),
                    title=name,
                    date=str(vintage) if vintage is not None else "",
                ))
            if len(hits) < ALGOLIA_PAGE_SIZE:
                break
            page += 1
        return refs

    def _algolia_page(self, session, page):
        url = ALGOLIA_QUERY_URL.format(index=ALGOLIA_INDEX)
        resp = session.post(
            url,
            headers=self._algolia_headers(),
            json={
                "query": "",
                "facetFilters": [["saleType:AUCTION"]],
                "hitsPerPage": ALGOLIA_PAGE_SIZE,
                "page": page,
                "attributesToRetrieve": ["id", "name", "vintage", "product"],
            },
        )
        return resp.json()

    def fetch(self, session, ref):
        body = self._load_page(session, ref.url)
        page_props = body.get("pageProps", {})
        if "__N_REDIRECT" in page_props:
            canonical = page_props["__N_REDIRECT"]
            slug = canonical.rstrip("/").rsplit("/", 1)[-1]
            body = self._load_page(session, self._next_data_url(slug))
            page_props = body.get("pageProps", {})
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data=page_props.get("productVintageRatings") or {},
        )

    @staticmethod
    def _load_page(session, url):
        return session.get(url, headers=IdealwineFetcher._next_headers()).json()
