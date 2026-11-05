"""Fetcher for iDealwine via Algolia enumeration + Next.js SSR data route.

iDealwine exposes no per-auction result feed. Adjudications (``soldAt`` +
``historicPrice``) live per wine in the "cote" (price history), reachable
only through the Next.js SSR data route of a concrete product-variant page.
The cote JSON API (``/api/v2/shop/product-vintage-rating-info/...``) returns
403 for direct clients.

As of a Nov 2026 site redesign, the cote no longer sits directly on
``pageProps`` -- it is one entry (queryKey ``["pdp-displayed-vintage-rating",
"<product>-<vintage>"]``) inside the page's dehydrated React-Query cache
(``pageProps.dehydratedState.queries``), and each ``lastAdjudications`` entry
was reduced to ``{id, soldAt, historicPrice}`` -- no more per-sale hammer
price, bottle count or wine identity. Wine identity (estate, region,
appellation, color) is instead captured once at discover() time from the
Algolia hit and carried through via ``AuctionRef.meta``; the per-variant
bottle count/format is read from the same page's
``syliusApiShopProductVariantGet`` query.

- discover: enumerate the currently offered lots via the Algolia ``prod_lots``
  index (fixed search-only key), requesting wine-identity attributes
  directly so they survive into ``AuctionRef.meta``.
- fetch: load ``/_next/data/{buildId}/{locale}/kaufen-ein-wein/{slug}.json``
  with ``x-nextjs-data: 1``, follow the SSR redirect to the canonical slug,
  and pull the cote + bottle-variant queries out of the dehydrated cache.

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
# Identity attributes pulled directly as hit fields (not just inside Algolia's
# highlight result) so they survive into AuctionRef.meta -- the SSR page no
# longer carries per-sale wine identity, only the Algolia search index does.
#
# No "classification" here (unlike the retired SSR-page field of the same
# name, e.g. GRAND_CRU/PREMIER_CRU): checked a real hit directly -- this
# index's own "category"/"productCategory" are a generic AOC/IG tier
# ("VINS_AOC_AVEC_IG_AOP"), the same value for a plain village wine and a
# Grand Cru alike. "Grand Cru" only ever appears inside the free-text
# "name" field here, with no separate structured attribute to request.
# idealwine_diff.py/build_db.py still thread a "classification" field
# through end to end, so every idealwine lot now gets classification=NULL
# -- not a bug in this module, there is simply nothing left to request.
ALGOLIA_IDENTITY_ATTRS = [
    "id", "name", "vintage", "product", "appellation", "domainName",
    "region", "color", "bottleSize",
]
RATING_QUERY_KEY = "pdp-displayed-vintage-rating"
VARIANT_QUERY_KEY = "syliusApiShopProductVariantGet"

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
                meta = {
                    "product_id": product,
                    "vintage": vintage,
                    "wine": name,
                    "estate": hit.get("domainName"),
                    "region": hit.get("region"),
                    "appellation": hit.get("appellation"),
                    "color": hit.get("color"),
                    "format": hit.get("bottleSize"),
                    # Carried through so fetch() can require an exact
                    # queryKey[1] match on the variant query below (see
                    # _find_query) instead of trusting the first query
                    # that merely starts with the right prefix.
                    "product_variant_id": pid,
                }
                refs.append(AuctionRef(
                    provider=self.provider,
                    auction_id=f"{product}-{vintage}",
                    url=self._next_data_url(f"{pid}-{slugify(name)}"),
                    title=name,
                    date=str(vintage) if vintage is not None else "",
                    meta=meta,
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
                "attributesToRetrieve": ALGOLIA_IDENTITY_ATTRS,
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
        queries = (page_props.get("dehydratedState") or {}).get("queries") or []
        # Confirmed real gap: matching only queryKey[0] (the prefix) would
        # return the FIRST query with that prefix regardless of which
        # product/variant it's actually for -- harmless while a lot page
        # only ever embeds one of each, but silently wrong the moment it
        # ever embeds a second one (e.g. a prefetched "related wine"
        # widget sharing the same page). queryKey[1] is this exact
        # product-vintage id (ref.auction_id, same format discover()
        # builds it in) / this exact variant id (meta.product_variant_id,
        # the Algolia hit's own id, carried through from discover()).
        rating = self._find_query(queries, RATING_QUERY_KEY, ref.auction_id)
        variant = self._find_query(
            queries, VARIANT_QUERY_KEY, ref.meta.get("product_variant_id"))
        variations = variant.get("variantVariations") or []
        meta = dict(ref.meta)
        meta["bottles"] = variations[0].get("numberOfBottles") if variations \
            else None
        if variations and variations[0].get("format"):
            meta["format"] = variations[0]["format"]
        # Known, unfixable-from-here limitation (not a bug in this
        # module): this single current variant's bottles/format gets
        # stamped onto every entry in lastAdjudications below, even
        # though those are several distinct historical sales. If the
        # same product+vintage was ever sold in more than one format
        # (e.g. both standard bottles and magnums), the older sales'
        # true format is wrong here. The site's current API gives no
        # per-sale bottle/format data at all any more (see the module
        # docstring -- lastAdjudications was reduced to
        # {id, soldAt, historicPrice}), so there is no data left to
        # recover this from; this fetcher only has whichever single
        # variant the page happens to currently offer.
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "meta": meta,
                "productVintageRatings": rating.get("productVintageRatings")
                or [],
                "lastAdjudications": rating.get("lastAdjudications") or [],
            },
        )

    @staticmethod
    def _find_query(queries, key_prefix, key_suffix):
        """Return the ``state.data`` of the dehydrated query whose
        ``queryKey`` is ``[key_prefix, key_suffix]``, or ``{}`` if absent.
        Both current callers always have a concrete ``key_suffix``."""
        for q in queries:
            key = q.get("queryKey") or []
            if not key or key[0] != key_prefix:
                continue
            if len(key) < 2 or str(key[1]) != str(key_suffix):
                continue
            return (q.get("state") or {}).get("data") or {}
        return {}

    @staticmethod
    def _load_page(session, url):
        return session.get(url, headers=IdealwineFetcher._next_headers()).json()
