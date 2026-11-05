"""Fetcher for ackerwines.com (Acker Merrall & Condit).

The WordPress front-end is behind a hard Cloudflare WAF block for a bare
user agent, but the actual data API (``api.ackerwines.com``) is a plain,
unauthenticated REST backend with no bot-detection layer of its own at
all -- confirmed Nov 2026: ``curl_cffi`` with chrome impersonation plus
``Accept``/``Content-Type``/``Referer``/``Origin`` headers reaches it with
no cookie, no Turnstile, no challenge of any kind. No browser needed.

- discover: there is no auction-listing endpoint that covers the site's
  full history -- ``GET /api/NapaAuctions?UpcomingOnly=false`` only returns
  ~37 recent/upcoming "Live" sales, never the recurring "Web" auctions
  (confirmed: auction 1706, a real closed Web auction, is absent from it).
  Both auction kinds instead share one ``auctionId`` space, and
  ``POST /api/NapaLots/Browse`` cleanly returns ``totalLots: 0`` for any
  unused id (no 404/500) -- so discovery is a sweep of that id space via
  ``NapaLots/Browse`` itself, not the auctions endpoint. The sweep starts
  at id 1 and stops once ``STOP_STREAK`` consecutive misses are seen
  *after* the first hit (never before -- counting misses from id 1 would
  end the sweep before the first real cluster below). The id space is
  **not** one dense block, confirmed via an exhaustive sweep of 1..1899
  (2026-11-03): 694 real hits in two separate clusters -- an early one at
  20-74, then a gap of exactly 1000 consecutive misses (75-1073), then a
  second, much denser cluster from 1074 up to the newest auction seen so
  far (1803; everything above that through at least 2500 was confirmed
  empty). The largest gap *within* the second cluster is only 23, so
  ``STOP_STREAK=1100`` clears the one real 1000-wide gap with margin
  while still stopping a reasonable distance (~1100 ids) past the current
  newest auction -- a smaller value (150 was tried first) silently stops
  inside the big gap and misses the entire second cluster, which is why
  an early production run archived only the 41 oldest auctions and
  nothing from the current/recent ones. Re-measure if a future run
  suddenly finds far fewer auctions than before -- that's the symptom of
  this threshold being too small for however the id space has shifted.
  Probed in batches of ``CONCURRENCY`` ids at once (see the note on
  ``CONCURRENCY`` below) rather than one at a time, but the miss-streak is
  still evaluated strictly in increasing id order within and across
  batches, so the stop point is identical to a fully sequential sweep.
- fetch: paginate ``NapaLots/Browse`` for one ``auctionId`` (the server
  fixes the page size at 100 regardless of ``recordsRequested``) --
  fetches page 1 to learn ``totalLots``, then follows the server's own
  cursor (``previousInitialLotId`` = the last lot's ``lotId``) one page
  at a time until ``totalLots`` lots are collected. ``pageRequested`` is
  a no-op, confirmed live; there is no page-level concurrency here,
  unlike ``discover()``'s per-id probes -- each page depends on the
  previous one's last lotId. Gated on the auction's own ``endDate`` --
  not yet closed raises, so it's retried next run rather than archived
  with no final price. ``soldPrice`` is confirmed useless (always 0 in a
  100-lot sample, sold or not) -- ``currentBid`` is the real hammer price
  on a closed lot; ``lotStatus`` ("S"/"NS") is sold/unsold, not
  ``soldPrice``. ``premium`` is an auction-level field (e.g. 0.25) read
  directly off each auction's own Browse response, not assumed from a
  global policy -- the buyer's premium and total price are computed from
  it here. No VAT/tax rate is documented anywhere for this house, so
  ``tax_amount`` is left unset (same as the other houses with no
  documented rate).
- A mixed lot (``isMixedLot: true``, multiple ``lotItems``) was not seen
  in the original 100-lot sample, but turned out to be common in
  production (21.7% of all rows in the first real run, confirmed
  2026-11-04) -- one row per ``lotItems`` entry sharing the same
  ``lot_no``, but (see ``_map_lot``) the lot's price fields only live on
  the first row, not repeated on every sibling, so a plain
  ``SUM(total_price)`` over the lots table counts each mixed lot's value
  exactly once.
"""
import datetime
import queue
import re
import threading
import time
import zoneinfo

from ..models import AuctionRef, FetchResult

BASE_URL = "https://api.ackerwines.com/api"
HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Referer": "https://www.ackerwines.com/",
    "Origin": "https://www.ackerwines.com",
}
# Confirmed real: auctionId query results are identical regardless of these
# two fields' value (date filtering is a no-op once auctionId is given), so
# any fixed, wide window is safe to hardcode.
_BODY_TEMPLATE = {
    "previousInitialLotId": "0", "recordsRequested": 100,
    "sortBy": "newest", "isArchiveSearch": False,
    "auctionDateStart": "Wed Jan 01 2020 00:00:00 GMT+0000",
    "auctionDateEnd": "Thu Jan 01 2032 00:00:00 GMT+0000",
    "search": "", "upcomingBidsLock": False, "myBidsLock": False,
    "unformattedSearch": "", "myBids": False, "watchedLots": False,
    "lotsWithNoBidsOnly": False, "mixedLotsOnly": False,
    "newLotsOnly": False, "mixedLots": False, "favoriteProducers": False,
    "singleBottleLotsOnly": False, "owcOnly": False, "onlyNewlots": False,
    "vintages": [], "myBidsList": [], "regions": [], "prices": [],
    "bottleSizes": [], "locations": [], "jumpToLot": "",
}
START_ID = 1
STOP_STREAK = 1100
_END_DATE_FMT = "%m/%d/%Y %I:%M:%S %p"
# Confirmed real: a single request to NapaLots/Browse can stall for several
# minutes with 0 bytes received (observed twice, independently, both times
# near 407s) despite an explicit ``timeout=30`` -- a transient stall on the
# remote end, not a client-side timeout bug (verified against a local slow
# server: curl_cffi's ``timeout=`` kwarg does abort a post-connect stall at
# the requested second). The discover() sweep alone is thousands of
# sequential requests, so one such stall must not kill the whole run.
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_S = 2
# Confirmed real (2026-11-03): despite the above, a production run wedged
# for 7+ hours inside a single curl_easy_perform/poll() call -- `sample`
# showed it stuck in cf_h2_recv/nghttp2_session_mem_recv2 the whole time,
# i.e. mid-HTTP/2-stream, not pre-response -- and curl's own ``timeout=30``
# never fired. A local repro confirmed timeout= DOES bound a mid-stream
# stall on plain HTTP/1.1, so this is specific to this host's long-lived
# HTTP/2 connection getting into a rare state curl's own timeout doesn't
# cover. A controlled comparison (same day, same endpoint) confirmed the
# fix: 8 fresh-session requests all completed in 1-4s each with zero
# stalls, so every Browse call below now opens its own short-lived session
# instead of reusing the one the caller passed in (connection reuse is the
# suspected trigger, not request volume -- a 40-call run on one shared
# session was fine too, so this is a rare, not deterministic, failure mode;
# fresh-per-call avoids it rather than proving why it happens). The hard
# wall-clock backstop (daemon thread, since curl isn't trustworthy to
# self-interrupt here) stays as cheap insurance against a residual stall.
HARD_TIMEOUT_S = 35
# Confirmed real (2026-11-03, later the same day): fresh-session-per-call
# alone was NOT enough -- a live production run with the fix above still
# only managed ~1 call/2.8s (measured via thread-creation rate over a 48s
# window), against 0.34-0.40s/call measured in isolation on the same API
# at the same time. `sample` on the live process caught two _post_once
# threads alive at once even though _post_with_retry only ever starts one
# attempt at a time -- proof that mid-stream stalls are still happening
# live, with or without session reuse, just recovered by the watchdog
# instead of wedging forever. So the stall is server-side and not fully
# avoidable client-side; the actual fix is to stop paying for it
# sequentially. discover()'s sweep (~1900 ids) overlaps its per-id probe
# calls instead of awaiting each one before starting the next -- a
# slow/stalling call no longer blocks the whole sweep behind it. This
# constant is used only there now: fetch()'s own pagination is NOT
# parallelized this way (see fetch()'s own comment -- the API's
# cursor-based pagination makes each page depend on the previous one's
# last lotId, so there is nothing to overlap). 8 is a deliberately
# conservative concurrency (this is a small auction house's API with no
# bot-detection layer at all, per the module docstring -- not a reason to
# hammer it harder than needed).
CONCURRENCY = 8


class AckerwinesFetcher:
    provider = "ackerwines"

    def discover(self, session):  # noqa: ARG002 -- see _post_with_retry
        refs = []
        found_any = False
        consecutive_zero = 0
        auction_id = START_ID
        while True:
            batch_ids = list(range(auction_id, auction_id + CONCURRENCY))
            requests_list = [
                (f"{BASE_URL}/NapaLots/Browse",
                 dict(_BODY_TEMPLATE, pageRequested=1, auctionId=aid))
                for aid in batch_ids]
            responses = _parallel_post(requests_list, CONCURRENCY,
                                       tolerant=True)
            stop = False
            for aid, resp in zip(batch_ids, responses):
                # resp is None when this id's probe failed all of
                # _post_with_retry's own attempts (see _parallel_post's
                # tolerant mode) -- treated the same as a 0-lot response:
                # an inconclusive miss, not a crash of the whole sweep.
                try:
                    total = (resp.json().get("totalLots") or 0
                             if resp is not None
                             and getattr(resp, "status_code", 200) == 200
                             else 0)
                except ValueError:
                    # Malformed/non-JSON 200 body: treated the same as the
                    # other inconclusive-miss cases in this tolerant sweep,
                    # not allowed to raise and abort the whole discover().
                    total = 0
                if total:
                    found_any = True
                    consecutive_zero = 0
                    # Confirmed real gap: a hit found later in this same
                    # batch, after an earlier id in it already crossed
                    # STOP_STREAK, must cancel that pending stop -- the
                    # miss streak is broken, exactly as it would be across
                    # batch boundaries, so the sweep must keep going past
                    # this batch too, not just stop anyway once the batch
                    # ends.
                    stop = False
                    refs.append(AuctionRef(
                        provider=self.provider, auction_id=str(aid),
                        url=f"{BASE_URL}/NapaLots/Browse?auctionId={aid}"))
                elif found_any:
                    consecutive_zero += 1
                    if consecutive_zero >= STOP_STREAK:
                        stop = True
                        # Confirmed real gap: breaking out of this loop the
                        # moment the streak crosses STOP_STREAK skips every
                        # id still left in THIS batch, even though their
                        # responses were already fetched by the
                        # _parallel_post call above (not pending -- already
                        # in `responses`). If one of those remaining ids is
                        # a genuine hit, it would otherwise be silently
                        # discarded, not just "not reached yet". Finish
                        # scoring every id already fetched in this batch
                        # (still in strict increasing order, just no
                        # longer short-circuited) before deciding whether
                        # to stop the outer sweep.
            if stop:
                break
            auction_id += CONCURRENCY
        return refs

    def fetch(self, session, ref):  # noqa: ARG002 -- see _post_with_retry
        auction_id = int(ref.auction_id)
        body = dict(_BODY_TEMPLATE, pageRequested=1, auctionId=auction_id)
        resp = _post_with_retry(f"{BASE_URL}/NapaLots/Browse", body)
        if getattr(resp, "status_code", 200) != 200:
            raise RuntimeError(
                f"ackerwines/{ref.auction_id}: HTTP {resp.status_code}")
        try:
            data = resp.json()
        except ValueError as exc:
            # Match _post_with_retry's RuntimeError-only contract: a
            # truncated/garbled 200 body must not escape as a raw
            # JSONDecodeError, or orchestrate.py's per-ref catch (which
            # only catches RuntimeError) would abort the whole provider
            # run instead of skipping just this ref.
            raise RuntimeError(
                f"ackerwines/{ref.auction_id}: invalid JSON response"
            ) from exc
        auction_meta = _find_batch(data, ref.auction_id)
        if auction_meta is None:
            raise RuntimeError(f"ackerwines/{ref.auction_id}: no data")
        lots = list(auction_meta.get("lots") or [])
        total_lots = data.get("totalLots")

        # Confirmed real (2026-11-05): `pageRequested` is a complete no-op
        # -- live-tested by requesting pages 1/2/3 of the same auction
        # with previousInitialLotId fixed at "0" (this fetcher's original
        # approach) and getting back the exact same 100 lots every time.
        # The API actually paginates via `previousInitialLotId` as a
        # cursor: set it to the *last* lot's `lotId` from the previous
        # call to get the next page. Confirmed this way across a full
        # 8-page auction. This is why every multi-page auction in the
        # archive was duplicated (689 of 691 files, 1.14M excess rows,
        # confirmed via `_check_duplicate_lot_numbers` in build_db.py) --
        # the old code requested "pages" 2..totalPage concurrently, all
        # with previousInitialLotId="0", so every one of them replayed
        # page 1.
        #
        # Pagination is therefore strictly sequential (each call needs
        # the previous call's last lotId) -- no more CONCURRENCY here,
        # unlike discover()'s independent per-id probes. It also cannot
        # stop on "empty response": confirmed live that once the cursor
        # is advanced past the last real lot, the API does not return
        # empty -- it wraps around and replays from the start again. The
        # only safe stop condition is reaching the server's own
        # `totalLots` count; a defensive no-new-ids check guards against
        # that wraparound (or any other cursor malfunction) looping
        # forever re-fetching the same page.
        seen_ids = {lot.get("lotId") for lot in lots}
        # Cursor must be the raw last lotId of the page actually returned
        # by the server, not of the dedup-filtered `lots` accumulator: if a
        # page's tail item happens to already be in seen_ids (e.g. a
        # wraparound duplicate landing right before the real next page),
        # filtering it out of `new_lots` would otherwise leave `lots[-1]`
        # pointing at an earlier id than the server's real cursor position.
        cursor_id = lots[-1].get("lotId") if lots else None
        while total_lots is not None and len(lots) < total_lots:
            body = dict(_BODY_TEMPLATE, pageRequested=1,
                        auctionId=auction_id,
                        previousInitialLotId=str(cursor_id))
            resp = _post_with_retry(f"{BASE_URL}/NapaLots/Browse", body)
            if getattr(resp, "status_code", 200) != 200:
                raise RuntimeError(
                    f"ackerwines/{ref.auction_id}: HTTP "
                    f"{resp.status_code}")
            try:
                page_json = resp.json()
            except ValueError as exc:
                raise RuntimeError(
                    f"ackerwines/{ref.auction_id}: invalid JSON response"
                ) from exc
            page_batch = _find_batch(page_json, ref.auction_id)
            if page_batch is None:
                raise RuntimeError(
                    f"ackerwines/{ref.auction_id}: no data")
            page_lots = page_batch.get("lots") or []
            if page_lots:
                cursor_id = page_lots[-1].get("lotId")
            new_lots = [lot for lot in page_lots
                       if lot.get("lotId") not in seen_ids]
            if not new_lots:
                break
            seen_ids.update(lot.get("lotId") for lot in new_lots)
            lots.extend(new_lots)

        if not lots:
            raise RuntimeError(f"ackerwines/{ref.auction_id}: no lots")
        if total_lots is not None and len(lots) < total_lots:
            # Pagination ended (loop-exit via `break` above, or a
            # genuinely short final page) before reaching the server's own
            # declared totalLots -- per the pagination comments above, that
            # count is the only safe completion signal, so stopping short
            # of it is always a partial fetch, never a legitimate "done"
            # state. Raise instead of returning a silently-partial lot
            # list: orchestrate.py's caller marks any non-raising result as
            # permanently fetched (mark_fetched), so a partial result here
            # would otherwise never be retried.
            raise RuntimeError(
                f"ackerwines/{ref.auction_id}: paginated {len(lots)}/"
                f"{total_lots} lots, stopped short")

        end_dt = _parse_end_date(auction_meta.get("endDate"))
        if end_dt is None:
            # Confirmed real gap (never actually observed -- every one of
            # the 691 auctions archived so far had a parseable endDate):
            # the closed-auction gate below only fires when end_dt is a
            # real, future-dated value. A missing/malformed endDate made
            # it fail OPEN (proceed to archive) instead of failing safe --
            # the one thing we must never do is archive a still-live
            # lotStatus/currentBid as if it were the final price with no
            # way to tell it wasn't.
            raise RuntimeError(
                f"ackerwines/{ref.auction_id}: endDate missing or "
                f"unparseable ({auction_meta.get('endDate')!r}), cannot "
                "confirm closed")
        if end_dt > datetime.datetime.now(
                tz=zoneinfo.ZoneInfo("America/New_York")):
            raise RuntimeError(
                f"ackerwines/{ref.auction_id}: not closed yet")

        premium_rate = auction_meta.get("premium")
        rows = []
        for lot in lots:
            rows.extend(_map_lot(lot, premium_rate, auction_id))

        return FetchResult(
            provider=self.provider, auction_id=ref.auction_id,
            data={
                "auction": {
                    "id": ref.auction_id,
                    "name": auction_meta.get("auctionName"),
                    "date": (end_dt.date().isoformat()
                             if end_dt else None),
                },
                "lots": rows,
            })


def _find_batch(data, auction_id):
    batches = data.get("auctionLots") or []
    return next((b for b in batches if str(b.get("auctionId")) == auction_id),
                None)


def _parallel_post(requests_list, concurrency, tolerant=False):
    """Runs ``_post_with_retry`` for each (url, body) pair with up to
    ``concurrency`` calls in flight at once, returning results in the same
    order as ``requests_list`` -- needed so callers can apply their own
    strictly-ordered logic (discover()'s consecutive-miss streak, fetch()'s
    page order) exactly as if the calls had run sequentially, just
    overlapped. Safe to await unconditionally -- every worker thread's
    call to _post_with_retry is itself bounded by
    HARD_TIMEOUT_S * RETRY_ATTEMPTS, so every thread is guaranteed to
    finish (success or raise) and release the semaphore.

    By default (``tolerant=False``, fetch()'s use -- a partial/missing
    page within one auction's lots is a real correctness problem) a call
    that still fails after all of _post_with_retry's own retries
    re-raises its exception once collection reaches it, same as a
    sequential call. With ``tolerant=True`` (discover()'s use) a failed
    call's slot holds ``None`` instead of raising: confirmed real gap --
    discover()'s ~1900-id sweep had no per-id isolation at all, so one
    persistently-failing id (all 3 of _post_with_retry's own attempts
    exhausted, not just a single transient blip) would abort the entire
    sweep instead of being logged and treated as an inconclusive miss."""
    results = [None] * len(requests_list)
    errors = [None] * len(requests_list)
    sem = threading.Semaphore(concurrency)
    threads = []

    def worker(i, url, body):
        try:
            results[i] = _post_with_retry(url, body)
        except Exception as exc:  # noqa: BLE001 -- re-raised by caller below
            errors[i] = exc
        finally:
            sem.release()

    for i, (url, body) in enumerate(requests_list):
        sem.acquire()
        t = threading.Thread(target=worker, args=(i, url, body), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    if tolerant:
        for i, exc in enumerate(errors):
            if exc is not None:
                print(f"ackerwines/discover: {requests_list[i][1].get('auctionId')}: "
                      f"{exc}, als Treffer-los behandelt", flush=True)
        return results
    for exc in errors:
        if exc is not None:
            raise exc
    return results


def _new_session():
    from curl_cffi import requests
    return requests.Session(impersonate="chrome")


def _post_once(session, url, body, result_q):
    try:
        resp = session.post(url, json=body, headers=HEADERS, timeout=30)
        if resp.status_code in (429, 500, 502, 503, 504):
            # Confirmed real gap: a transient 5xx/429 was previously
            # treated as "ok" here (no exception raised), so it bypassed
            # the retry loop entirely and discover() silently coerced it
            # to totalLots=0 -- indistinguishable from a genuine empty
            # id, dropping a real auction from the sweep with no retry
            # and no log. Route it through the same retry path as a
            # network-level failure instead. A 404 (or other 4xx) is left
            # as "ok" -- this API returns 200/totalLots:0 for every known
            # empty id, so a 4xx here is itself unusual/stable, not a
            # transient server hiccup worth retrying.
            result_q.put(("err", RuntimeError(
                f"HTTP {resp.status_code} from {url}")))
            return
        result_q.put(("ok", resp))
    except Exception as exc:  # noqa: BLE001 -- any curl_cffi/network error
        result_q.put(("err", exc))


def _post_with_retry(url, body, attempts=RETRY_ATTEMPTS):
    """POST on a fresh, short-lived session -- re-raises the last error once
    all ``attempts`` are exhausted. Deliberately ignores any session the
    caller holds (see the confirmed-real note on HARD_TIMEOUT_S above: a
    long-lived, reused connection is the suspected trigger for the rare
    multi-hour wedge, and fresh-per-call measurably avoids it). Each attempt
    runs in a daemon thread so a hung curl call that never returns cannot
    block the process -- it's simply abandoned once HARD_TIMEOUT_S elapses.
    """
    last_exc = None
    for attempt in range(attempts):
        result_q = queue.Queue(maxsize=1)
        t = threading.Thread(target=_post_once,
                             args=(_new_session(), url, body, result_q),
                             daemon=True)
        t.start()
        try:
            kind, payload = result_q.get(timeout=HARD_TIMEOUT_S)
        except queue.Empty:
            kind, payload = "err", TimeoutError(
                f"hard watchdog: no response within {HARD_TIMEOUT_S}s "
                "(curl's own timeout did not fire)")
        if kind == "ok":
            return payload
        last_exc = payload
        if attempt < attempts - 1:
            time.sleep(RETRY_BACKOFF_S * (attempt + 1))
    # Confirmed real: orchestrate.py's per-ref loop only catches
    # RuntimeError to skip one bad ref and continue (every other fetcher's
    # own raises already follow this contract) -- re-raising last_exc's
    # own type (curl_cffi's exception classes, or the synthetic
    # TimeoutError above) bypasses that catch entirely, aborting the
    # whole provider run (skipping set_last_run/save_manifest) instead of
    # just skipping this one ref.
    raise RuntimeError(f"ackerwines: {last_exc}") from last_exc


def _map_lot(lot, premium_rate, auction_id):
    sold = lot.get("lotStatus") == "S"
    hammer = lot.get("currentBid") if sold else None
    buyer_premium = (round(hammer * premium_rate, 2)
                     if hammer is not None and premium_rate is not None
                     else None)
    total_price = (hammer + buyer_premium
                   if hammer is not None and buyer_premium is not None
                   else hammer)
    currency = lot.get("currencySymbol") or "USD"
    lot_no = lot.get("lotNo")
    lot_id = lot.get("lotId")
    items = lot.get("lotItems") or [{}]
    rows = []
    for i, item in enumerate(items):
        # Confirmed real (2026-11-04): mixed lots (multiple distinct
        # wines under one shared hammer price) are NOT rare -- 21.7% of
        # all rows in the first production run, not "never observed" as
        # this module's docstring originally claimed. Every house's
        # other mixed-lot handling (e.g. weinboerse) keeps the lot's
        # price on exactly one row; repeating the FULL lot price on
        # every sibling item row here meant a naive SUM(total_price)
        # over the lots table double/triple/quadruple-counted every
        # mixed lot's value by however many items it had. Only the
        # first item's row carries the price now; the rest share
        # lot_no/source_lot_key (so they're still identifiable as one
        # lot) but price fields are None, same convention as an unsold
        # lot's "no final price" rows elsewhere in this fetcher.
        is_priced_row = i == 0
        rows.append({
            "lot_no": str(lot_no) if lot_no is not None else None,
            "source_lot_key": (f"ackerwines:{lot_id}" if lot_id is not None
                               else None),
            "wine": item.get("wineName"),
            "producer": item.get("producerName"),
            "vintage": _to_int(item.get("vintage")),
            "region": item.get("region") or None,
            "appellation": item.get("appellation") or None,
            "condition_text": item.get("condition") or None,
            # Explicit None/empty check, not `or None`: a genuine
            # wineScore of 0 (falsy but valid) must not be dropped the
            # same way a missing score is.
            "note": (item.get("wineScore")
                     if item.get("wineScore") not in (None, "") else None),
            "quantity": item.get("bottleQuantity"),
            "bottle_size_raw": item.get("bottleSize"),
            "estimate_low": lot.get("estimateLow") if is_priced_row else None,
            "estimate_high": (lot.get("estimateHigh") if is_priced_row
                              else None),
            "hammer_price": hammer if is_priced_row else None,
            "buyer_premium": buyer_premium if is_priced_row else None,
            "realised_price": total_price if is_priced_row else None,
            "total_price": total_price if is_priced_row else None,
            "price_basis": ("HAMMER" if is_priced_row and hammer is not None
                            else "UNKNOWN" if is_priced_row else None),
            "currency": currency,
            "sold": sold if is_priced_row else None,
            "mixed_lot": bool(lot.get("isMixedLot")),
            "source_url": (f"{BASE_URL}/NapaLots/Browse"
                           f"?auctionId={auction_id}"
                           f"&lotId={lot.get('originalLotID')}"),
        })
    return rows


def _parse_end_date(text):
    """Confirmed real (2026-11-03): ``endDate`` is US Eastern, not UTC --
    the live site itself says e.g. "closes Sunday, November 8 at 8pm ET!"
    for one sale. Comparing the naive parsed value against a naive
    ``datetime.now()`` (as this fetcher originally did) silently assumes
    the caller's own clock is also Eastern -- true on a dev machine set to
    US time, false on a GitHub Actions runner (UTC) or any other timezone,
    where a sale still hours from closing in Eastern would already read as
    "closed" and have its non-final ``currentBid`` archived as if final.
    Localized to America/New_York (handles DST correctly, unlike a fixed
    UTC-5/-4 offset) so the comparison in fetch() is timezone-aware."""
    if not text:
        return None
    try:
        naive = datetime.datetime.strptime(text, _END_DATE_FMT)
    except ValueError:
        return None
    return naive.replace(tzinfo=zoneinfo.ZoneInfo("America/New_York"))


def _to_int(v):
    """Same tolerance as build_db.to_int (not imported -- fetchers don't
    depend on the data/ loader layer): strips thousands-separators and
    regex-extracts digits rather than requiring the whole string to
    already be a bare int. No real ackerwines vintage sampled so far
    (live API + 100 archived auctions) has needed this -- genuinely
    non-vintage items (Champagne, whisky) come through as "NV"/None,
    which this still correctly maps to None -- but it's a strict
    superset of the plain int() this replaces, so it only gains
    coverage."""
    if v is None or v == "":
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if s in ("", "null", "None"):
        return None
    m = re.search(r"-?\d+", s.replace(",", ""))
    return int(m.group()) if m else None
