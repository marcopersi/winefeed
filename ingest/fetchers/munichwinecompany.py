"""Fetcher for munichwinecompany.com.

The site was rebuilt as an Alpine.js SPA backed by a separate headless
CMS (cms.munichwinecompany.eu/api) at some point after the old
archive's last snapshot (auction-299, June 2024) -- the old
"/de/{id}/live-wineauction-pN.html" scrape URL now 404s. Confirmed via
the site's own bundled JS (stores.js's commented-out
``callApi('auctions/'+auctionId+'/wines'+query, ...)``): the real data
lives at ``GET {API_BASE}/auctions/{id}/wines?all=1``, no login
needed, just the plain PHPSESSID/CSRF-TOKEN cookies a normal page load
sets.

- discover: ``GET {API_BASE}/auctions`` (no id) returns the currently
  visible "online"/"live"/"upcomingOnline"/"upcomingLive" slots.
  Confirmed real constraints:
  - the "live" (catalog-style) auction format has been discontinued
    per that response's own text ("Unsere Katalogauktionen sind
    eingestellt" / "Our catalogue auctions have been discontinued"),
    so only "online" ever yields anything going forward.
  - ``/auctions/{id}/wines`` only returns real data while that auction
    is still within its aftersale window -- confirmed by probing every
    id 300-341 directly (only the one auction whose aftersale window
    was still open returned data) and by trying ``?aftersale=1`` on an
    old, long-closed id (still ``{"success": false}``). Auctions from
    before the site rebuild, and any that have since aged out of their
    aftersale window, are NOT reachable through this API -- a gap of
    the same kind as koppe's missing-2025 hole, left unresolved here;
    this fetcher only ever catches an auction while it's still fresh.
- fetch: ``GET {API_BASE}/auctions/{id}/wines?all=1``, returns
  ``{"items": [...]}``; each item's ``bid`` is null for an unsold lot.
"""
import datetime
import json

from ..models import AuctionRef, FetchResult

API_BASE = "https://cms.munichwinecompany.eu/api"
COOKIE_SEED_URL = "https://www.munichwinecompany.com/"


def _parse_json(resp):
    if hasattr(resp, "json"):
        try:
            return resp.json()
        except ValueError:
            pass
    return json.loads(resp.text)


class MunichWineCompanyFetcher:
    provider = "munich-wine-company"

    def discover(self, session):
        session.get(COOKIE_SEED_URL)  # seeds PHPSESSID + CSRF-TOKEN cookies
        data = _parse_json(session.get(f"{API_BASE}/auctions"))
        if not data.get("success"):
            return []
        slots = data.get("data") or {}
        refs = []
        seen = set()
        for key in ("online", "live"):
            slot = slots.get(key)
            if not slot or not slot.get("id"):
                continue
            aid = str(slot["id"])
            if aid in seen:
                continue
            seen.add(aid)
            # Skip a slot whose bidding is still open: "online" is
            # returned for an auction currently live, not just one past
            # its close that's sitting in its aftersale window (see
            # module docstring). Fetching while open would capture the
            # current bid as if it were the final hammer price, and the
            # manifest would mark the auction fetched so it's never
            # refetched after it actually closes.
            date_end = slot.get("date_end") or ""
            if date_end:
                try:
                    end_dt = datetime.datetime.fromisoformat(
                        date_end.replace("Z", "+00:00"))
                    if end_dt > datetime.datetime.now(datetime.timezone.utc):
                        continue
                except ValueError:
                    pass
            refs.append(AuctionRef(
                provider=self.provider, auction_id=aid,
                url=f"{API_BASE}/auctions/{aid}/wines?all=1",
                title=slot.get("name"),
                date=(slot.get("date_end") or "")[:10]))
        return refs

    def fetch(self, session, ref):
        data = _parse_json(session.get(ref.url))
        items = data.get("items") or []
        lots = []
        for it in items:
            lots.append({
                "lot_no": it.get("catalogue_nr"),
                "name": it.get("wine"),
                "brand": it.get("producer"),
                "vintage": it.get("year"),
                "region": ", ".join(
                    p for p in (it.get("area"), it.get("country")) if p)
                or None,
                "count_fill": it.get("bottle_count"),
                "hammer_price": it.get("bid"),
                "currency": "EUR",
                "description": it.get("desc"),
                "estimate_low": it.get("low"),
                "estimate_high": it.get("high"),
            })
        return FetchResult(
            provider=self.provider, auction_id=ref.auction_id,
            data={"auction": {"id": ref.auction_id, "title": ref.title,
                              "date": ref.date, "currency": "EUR",
                              "snapshot_timestamp": None},
                  "lots": lots})
