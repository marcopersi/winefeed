"""Fetcher for iDealwine via a known-products seed + Next.js SSR data route.

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
price, bottle count or wine identity. The per-variant bottle count/format is
read from the same page's ``syliusApiShopProductVariantGet`` query.

Confirmed real, unfixable-from-here limitation: ``lastAdjudications`` is
capped at the 10 most recent sales per product/vintage (confirmed via a
500-file sample of the archive: the adjudication-count distribution falls
off smoothly from 1 to 9 but spikes back up at exactly 10 -- a clear cap
signal, not coincidence; this predates this module's Nov 2026 rewrite, the
same cap is visible in the old Algolia-era archive too). A product/vintage
sold more than 10 times between two checkpoints silently loses whichever
sales fall outside the 10 most recent -- a bigger risk after an unusually
long gap between runs (this module's own catch-up after the dead-Algolia
period hit this for ~0.8% of re-polled products) than under normal monthly
cadence.

Enumeration (discover) used to go through the Algolia ``prod_lots`` index via
a branded proxy host (``algolia.idealwine.com``). That host is PERMANENTLY
DEAD (confirmed NXDOMAIN from two independent networks, 2026-11-24/25) --
the site's own current listing page still queries Algolia server-side
(same index, same facets, confirmed via its embedded SSR ``serverState``),
but the real current host/credentials the browser uses for live pagination
could not be found via static asset inspection (build manifest, every JS
chunk reachable from the listing page, several URL/slug filter guesses) --
that would need an actual browser network trace, not available here.

Given that, ``discover_known_products`` replaces live enumeration with a
static snapshot (``data/idealwine_known_products.json``, one entry per
(product, vintage) pair already present in the archive, each carrying one
of that pair's own past adjudication ``code``s -- confirmed live that even
a long-sold, several-months-old ``code`` still resolves to the product's
current SSR page, so there's no need to track a "currently for sale" id).
This is a deliberate, narrower replacement: it re-polls wines ALREADY KNOWN
to the archive for newly added adjudications, but can never discover a
brand-new wine that has no prior entry -- see the module's own docstring
note in ``run_idealwine_delta.py`` for how to regenerate the snapshot.

- discover_known_products: build one AuctionRef per snapshot entry, reusing
  its saved identity fields (wine/estate/region/appellation/color/
  classification) directly as ``AuctionRef.meta``, no HTTP call needed.
- fetch: load ``/_next/data/{buildId}/{locale}/kaufen-ein-wein/{slug}.json``
  with ``x-nextjs-data: 1``, follow the SSR redirect to the canonical slug,
  and pull the cote + bottle-variant queries out of the dehydrated cache.
  Confirmed still working unchanged after the Nov 2026 redesign (tested
  live against several current and long-settled lots).

The ``build_id`` is deployment-specific and changes with every release; it is
read from ``__NEXT_DATA__`` in the site HTML.
"""
import re
import unicodedata

from ..models import AuctionRef, FetchResult

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

    def discover_known_products(self, session, known_products):
        """Build one ``AuctionRef`` per entry of the ``data/
        idealwine_known_products.json`` snapshot (see module docstring) --
        no network enumeration call, just the current ``build_id``."""
        self._ensure_build_id(session)
        refs = []
        for entry in known_products:
            product = entry.get("product_id")
            vintage = entry.get("vintage")
            code = entry.get("code")
            name = entry.get("wine") or ""
            if product is None or not code:
                continue
            meta = {
                "product_id": product,
                "vintage": vintage,
                "wine": name,
                "estate": entry.get("estate"),
                "region": entry.get("region"),
                "appellation": entry.get("appellation"),
                "color": entry.get("color"),
                "classification": entry.get("classification"),
                # Fallback only: fetch() overwrites this with the live
                # page's current variant format when a match is found.
                # Review finding (2026-11-25): without this, a snapshot
                # entry whose current SSR page no longer embeds a
                # matching variant query (e.g. a long-delisted lot) would
                # silently end up with format=None instead of the
                # archive's own last-known format for that adjudication.
                "format": entry.get("format"),
                # Carried through so fetch() can require an exact
                # queryKey[1] match on the variant query below (see
                # _find_query) instead of trusting the first query
                # that merely starts with the right prefix.
                "product_variant_id": code,
            }
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=f"{product}-{vintage}",
                url=self._next_data_url(f"{code}-{slugify(name)}"),
                title=name,
                date=str(vintage) if vintage is not None else "",
                meta=meta,
            ))
        return refs

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
        # product-vintage id (ref.auction_id, same format
        # discover_known_products() builds it in) / this exact variant id
        # (meta.product_variant_id, the snapshot entry's own adjudication
        # code, carried through from discover_known_products()).
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
