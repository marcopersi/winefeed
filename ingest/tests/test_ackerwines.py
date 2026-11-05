import datetime
import unittest
import zoneinfo

from ingest.fetchers.ackerwines import (AckerwinesFetcher, _map_lot,
                                        _parse_end_date, _to_int)
from ingest.models import AuctionRef

SOLD_LOT = {
    "lotId": 946033, "originalLotID": "946033", "lotNo": 37362,
    "isMixedLot": False, "currencySymbol": "USD",
    "estimateLow": 4800, "estimateHigh": 6000, "lotStatus": "S",
    "soldPrice": 0, "currentBid": 4500,
    "lotItems": [
        {"wineName": "Montrachet", "producerName":
         "Domaine de la Romanee Conti", "appellation": "",
         "region": "White Burgundy", "vintage": "1995",
         "condition": "bsl, tl, ssos", "bottleQuantity": 1,
         "bottleSize": "bottle", "wineScore": "(99pts)"},
    ],
}
UNSOLD_LOT = dict(SOLD_LOT, lotId=1, originalLotID="1", lotStatus="NS",
                  currentBid=0, soldPrice=0)
MIXED_LOT = dict(SOLD_LOT, lotId=2, originalLotID="2", isMixedLot=True,
                 lotItems=[SOLD_LOT["lotItems"][0],
                          dict(SOLD_LOT["lotItems"][0],
                               wineName="La Tache")])


class MapLotTest(unittest.TestCase):
    def test_sold_lot_computes_premium_from_observed_auction_rate(self):
        rows = _map_lot(SOLD_LOT, 0.25, 1706)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lot_no"], "37362")
        self.assertEqual(row["wine"], "Montrachet")
        self.assertEqual(row["producer"], "Domaine de la Romanee Conti")
        self.assertEqual(row["vintage"], 1995)
        self.assertEqual(row["region"], "White Burgundy")
        self.assertIsNone(row["appellation"])
        self.assertTrue(row["sold"])
        self.assertEqual(row["hammer_price"], 4500)
        self.assertEqual(row["buyer_premium"], 1125.0)
        self.assertEqual(row["total_price"], 5625.0)
        self.assertEqual(row["currency"], "USD")
        self.assertEqual(row["source_lot_key"], "ackerwines:946033")

    def test_unsold_lot_has_no_hammer_price_even_though_currentbid_is_zero(
            self):
        rows = _map_lot(UNSOLD_LOT, 0.25, 1706)
        row = rows[0]
        self.assertFalse(row["sold"])
        self.assertIsNone(row["hammer_price"])
        self.assertIsNone(row["buyer_premium"])

    def test_mixed_lot_emits_one_row_per_item_sharing_lot_no(self):
        rows = _map_lot(MIXED_LOT, 0.25, 1706)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["lot_no"], rows[1]["lot_no"])
        self.assertEqual(rows[1]["wine"], "La Tache")
        self.assertTrue(rows[0]["mixed_lot"])
        self.assertTrue(rows[1]["mixed_lot"])

    def test_mixed_lot_price_lives_on_the_first_row_only(self):
        """Confirmed real (2026-11-04): mixed lots are 21.7% of all rows
        in the first production run, not "never observed" -- repeating
        the full lot price on every sibling item row meant a naive
        SUM(total_price) over the lots table double/triple-counted every
        mixed lot's value. Only the first item's row may carry it."""
        rows = _map_lot(MIXED_LOT, 0.25, 1706)
        self.assertEqual(rows[0]["hammer_price"], 4500)
        self.assertEqual(rows[0]["total_price"], 5625.0)
        self.assertIsNone(rows[1]["hammer_price"])
        self.assertIsNone(rows[1]["buyer_premium"])
        self.assertIsNone(rows[1]["total_price"])
        self.assertIsNone(rows[1]["realised_price"])
        self.assertIsNone(rows[1]["price_basis"])
        self.assertIsNone(rows[1]["sold"])


class ToIntTest(unittest.TestCase):
    def test_strips_thousands_separator_and_surrounding_text(self):
        self.assertEqual(_to_int("1,995"), 1995)
        self.assertEqual(_to_int("1995 (original release)"), 1995)
        self.assertEqual(_to_int("1995"), 1995)
        self.assertEqual(_to_int(1995), 1995)

    def test_non_vintage_text_is_none_not_an_error(self):
        self.assertIsNone(_to_int("NV"))
        self.assertIsNone(_to_int(None))
        self.assertIsNone(_to_int(""))


class ParseEndDateTest(unittest.TestCase):
    def test_localizes_to_us_eastern_not_naive(self):
        """Confirmed real: the live site states sale end times in ET
        (e.g. "closes Sunday, November 8 at 8pm ET!") -- comparing the
        naive parsed value straight against a naive datetime.now() (as
        this used to) silently assumes the caller's own clock is also
        Eastern, which is false on a UTC CI runner and would archive a
        still-live lot's currentBid as if it were the final price hours
        before the sale actually closed in Eastern time."""
        end_dt = _parse_end_date("11/22/2026 1:00:00 AM")
        self.assertEqual(end_dt.tzinfo, zoneinfo.ZoneInfo("America/New_York"))
        # Nov 22 is past the US DST switch-back, so this is EST (UTC-5) --
        # the same wall-clock instant is 06:00 UTC, 5h later than the
        # naive "1am" a UTC-based comparison would have used unlabeled.
        as_utc = end_dt.astimezone(datetime.timezone.utc)
        self.assertEqual(as_utc, datetime.datetime(2026, 11, 22, 6, 0, 0,
                                                    tzinfo=datetime.timezone.utc))


class DiscoverTest(unittest.TestCase):
    def test_sweeps_past_a_long_leading_deadzone_before_counting_misses(
            self):
        """Confirmed real: ids 1/100/1000 cleanly return totalLots=0 --
        counting misses from id 1 must not end the sweep before the real
        auctions (which only start well above 1000) are ever reached.
        Also covers batched/concurrent probing: CONCURRENCY is left at its
        real (>1) value here on purpose, so the miss-streak must still be
        evaluated in strict increasing-id order within and across
        batches, not just when probed one id at a time."""
        f = AckerwinesFetcher()
        valid_ids = {1500, 1501, 1502}

        class FakeResp:
            def __init__(self, total):
                self.status_code = 200
                self._total = total

            def json(self):
                return {"totalLots": self._total}

        class FakeSession:
            def post(self, url, json, headers, timeout):
                aid = json["auctionId"]
                return FakeResp(100 if aid in valid_ids else 0)

        import ingest.fetchers.ackerwines as mod
        old_stop = mod.STOP_STREAK
        old_new_session = mod._new_session
        mod.STOP_STREAK = 5
        mod._new_session = lambda: FakeSession()  # each call gets a fresh one
        try:
            refs = f.discover(FakeSession())  # session arg is unused, see fetcher
        finally:
            mod.STOP_STREAK = old_stop
            mod._new_session = old_new_session
        self.assertEqual([r.auction_id for r in refs],
                         ["1500", "1501", "1502"])

    def test_does_not_drop_a_hit_later_in_the_same_batch_as_the_stop(self):
        """Confirmed real gap: _parallel_post fetches a whole batch's
        responses up front, but the scoring loop used to `break` out the
        moment the miss-streak crossed STOP_STREAK -- discarding every
        remaining id already fetched in that same batch, even a genuine
        hit among them, instead of just stopping the sweep after it. A
        hit later in the batch must also cancel the pending stop (same as
        it would across a batch boundary), so the sweep keeps going."""
        f = AckerwinesFetcher()
        valid_ids = {50, 55}

        class FakeResp:
            def __init__(self, total):
                self.status_code = 200
                self._total = total

            def json(self):
                return {"totalLots": self._total}

        class FakeSession:
            def post(self, url, json, headers, timeout):
                aid = json["auctionId"]
                return FakeResp(100 if aid in valid_ids else 0)

        import ingest.fetchers.ackerwines as mod
        old_stop, old_concurrency = mod.STOP_STREAK, mod.CONCURRENCY
        old_new_session = mod._new_session
        # Batch [49-56] contains both the hit at 50 (starts the streak),
        # three misses that cross STOP_STREAK=3 at id 53, AND the later
        # hit at 55 that must still be captured and must keep the sweep
        # going past this batch.
        mod.STOP_STREAK = 3
        mod.CONCURRENCY = 8
        mod.START_ID = 1
        mod._new_session = lambda: FakeSession()
        try:
            refs = f.discover(FakeSession())
        finally:
            mod.STOP_STREAK = old_stop
            mod.CONCURRENCY = old_concurrency
            mod._new_session = old_new_session
        self.assertEqual([r.auction_id for r in refs], ["50", "55"])

    def test_survives_one_persistently_failing_id(self):
        """Confirmed real gap: before tolerant=True, one id exhausting
        all retry attempts raised out of the whole discover() sweep --
        every other real auction found so far in that run was lost, not
        just the one bad id."""
        f = AckerwinesFetcher()
        valid_ids = {1500, 1501, 1502}
        poison_id = 1499

        class FakeResp:
            def __init__(self, total):
                self.status_code = 200
                self._total = total

            def json(self):
                return {"totalLots": self._total}

        class FakeSession:
            def post(self, url, json, headers, timeout):
                aid = json["auctionId"]
                if aid == poison_id:
                    raise TimeoutError("persistently stalled")
                return FakeResp(100 if aid in valid_ids else 0)

        import ingest.fetchers.ackerwines as mod
        old_stop = mod.STOP_STREAK
        old_new_session = mod._new_session
        old_sleep = mod.time.sleep
        mod.STOP_STREAK = 5
        mod._new_session = lambda: FakeSession()
        mod.time.sleep = lambda _s: None  # keep retry backoff fast
        try:
            refs = f.discover(FakeSession())
        finally:
            mod.STOP_STREAK = old_stop
            mod._new_session = old_new_session
            mod.time.sleep = old_sleep
        self.assertEqual([r.auction_id for r in refs],
                         ["1500", "1501", "1502"])


class FetchPaginationTest(unittest.TestCase):
    """Covers fetch()'s cursor-based pagination: `pageRequested` is a
    no-op on the real API (confirmed 2026-11-05) -- the server paginates
    via `previousInitialLotId`, set to the *previous* call's last
    `lotId`. Pages are therefore fetched sequentially, one cursor hop at
    a time, until `totalLots` lots are collected."""

    def setUp(self):
        import ingest.fetchers.ackerwines as mod
        self._mod = mod
        self._new_session = mod._new_session

    def tearDown(self):
        self._mod._new_session = self._new_session

    def test_merges_pages_in_order(self):
        auction_id = 1706
        auction_name = "Web Auction 1706"
        end_date = "01/01/2020 12:00:00 AM"  # closed
        # Keyed by the cursor (previousInitialLotId) the real API expects
        # for each call: "0" for the first page, then the previous
        # page's last lotId.
        pages_by_cursor = {
            "0": [dict(SOLD_LOT, lotId=1, originalLotID="1")],
            "1": [dict(SOLD_LOT, lotId=2, originalLotID="2")],
            "2": [dict(SOLD_LOT, lotId=3, originalLotID="3")],
        }

        class FakeResp:
            def __init__(self, lots):
                self.status_code = 200
                self._lots = lots

            def json(self):
                return {
                    "totalLots": 3,
                    "auctionLots": [{
                        "auctionId": auction_id,
                        "auctionName": auction_name,
                        "endDate": end_date,
                        "premium": 0.25,
                        "lots": self._lots,
                    }],
                }

        class FakeSession:
            def post(self, url, json, headers, timeout):
                cursor = json["previousInitialLotId"]
                return FakeResp(pages_by_cursor[cursor])

        self._mod._new_session = lambda: FakeSession()
        f = AckerwinesFetcher()
        ref = AuctionRef(provider="ackerwines", auction_id=str(auction_id),
                         url="http://x")
        result = f.fetch(FakeSession(), ref)
        self.assertEqual([r["source_lot_key"] for r in result.data["lots"]],
                         ["ackerwines:1", "ackerwines:2", "ackerwines:3"])

    def test_stops_instead_of_looping_forever_when_cursor_stalls(self):
        """Confirmed real (2026-11-05): past the last real lot, the API
        does not return an empty page -- it wraps around and replays
        page 1 forever instead. This is also exactly the bug this fix
        replaces: the old code sent previousInitialLotId="0" on every
        "page" call, so every call replayed page 1 (689 of 691 archived
        files ended up duplicated this way, 1.14M excess rows). A plain
        "keep calling until totalLots is reached" loop would spin
        forever against a totalLots the cursor can never actually reach
        -- the no-new-lotId guard must break out of the loop, and the
        short-of-totalLots check below it must then raise (not return the
        partial 1-lot result as if it were a complete, final fetch) --
        orchestrate.py marks any non-raising result permanently fetched,
        so a silent partial result here would never be retried."""
        auction_id = 1706
        page1_lots = [dict(SOLD_LOT, lotId=1, originalLotID="1")]

        class FakeResp:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {
                    "totalLots": 999,  # never reachable -- server replays
                    "auctionLots": [{
                        "auctionId": auction_id,
                        "auctionName": "x",
                        "endDate": "01/01/2020 12:00:00 AM",
                        "premium": 0.25,
                        "lots": page1_lots,
                    }],
                }

        class FakeSession:
            def post(self, url, json, headers, timeout):
                return FakeResp()

        self._mod._new_session = lambda: FakeSession()
        f = AckerwinesFetcher()
        ref = AuctionRef(provider="ackerwines", auction_id=str(auction_id),
                         url="http://x")
        with self.assertRaises(RuntimeError):
            f.fetch(FakeSession(), ref)

    def test_missing_end_date_raises_instead_of_archiving_as_closed(self):
        """Confirmed real gap (never actually observed -- every archived
        auction so far had a parseable endDate): a missing/malformed
        endDate made the closed-auction gate fail OPEN (archive a
        possibly still-live currentBid as the final price) instead of
        failing safe."""
        auction_id = 1706

        class FakeResp:
            def __init__(self):
                self.status_code = 200

            def json(self):
                return {
                    "totalPage": 1,
                    "currentPage": 1,
                    "auctionLots": [{
                        "auctionId": auction_id,
                        "auctionName": "x",
                        "endDate": "",  # missing/unparseable
                        "premium": 0.25,
                        "lots": [dict(SOLD_LOT, lotId=1,
                                     originalLotID="1")],
                    }],
                }

        class FakeSession:
            def post(self, url, json, headers, timeout):
                return FakeResp()

        self._mod._new_session = lambda: FakeSession()
        f = AckerwinesFetcher()
        ref = AuctionRef(provider="ackerwines", auction_id=str(auction_id),
                         url="http://x")
        with self.assertRaises(RuntimeError):
            f.fetch(FakeSession(), ref)


class ParallelPostTest(unittest.TestCase):
    def setUp(self):
        import ingest.fetchers.ackerwines as mod
        self._mod = mod
        self._new_session = mod._new_session
        self._sleep = mod.time.sleep
        mod.time.sleep = lambda _s: None  # keep retry backoff fast in tests

    def tearDown(self):
        self._mod._new_session = self._new_session
        self._mod.time.sleep = self._sleep

    def test_preserves_input_order_despite_varying_latency(self):
        import threading
        import time

        from ingest.fetchers.ackerwines import _parallel_post

        class FakeResp:
            def __init__(self, n):
                self.status_code = 200
                self.n = n

        class SlowFirstSession:
            def post(self, url, json, headers, timeout):
                if json["n"] == 0:
                    time.sleep(0.2)  # first request resolves last
                return FakeResp(json["n"])

        self._mod._new_session = lambda: SlowFirstSession()
        requests_list = [("http://x", {"n": i}) for i in range(5)]
        results = _parallel_post(requests_list, concurrency=5)
        self.assertEqual([r.n for r in results], [0, 1, 2, 3, 4])

    def test_reraises_a_failure_from_any_worker(self):
        from ingest.fetchers.ackerwines import _parallel_post

        class FailsOnOddSession:
            def post(self, url, json, headers, timeout):
                if json["n"] % 2:
                    raise TimeoutError("stalled")
                return _Resp()

        class _Resp:
            status_code = 200

        self._mod._new_session = lambda: FailsOnOddSession()
        requests_list = [("http://x", {"n": i}) for i in range(4)]
        # _post_with_retry wraps its last_exc in a RuntimeError (the
        # orchestrate.py fetcher contract -- see its own comment), so
        # that's what _parallel_post re-raises here too.
        with self.assertRaises(RuntimeError):
            _parallel_post(requests_list, concurrency=4)

    def test_tolerant_mode_holds_none_instead_of_raising(self):
        """Confirmed real gap: discover()'s ~1900-id sweep had no per-id
        isolation -- one persistently-failing id (all 3 retry attempts
        exhausted) would abort the whole sweep. tolerant=True is what
        discover() now uses to survive that."""
        from ingest.fetchers.ackerwines import _parallel_post

        class FailsOnOddSession:
            def post(self, url, json, headers, timeout):
                if json["n"] % 2:
                    raise TimeoutError("stalled")
                return _Resp()

        class _Resp:
            status_code = 200

        self._mod._new_session = lambda: FailsOnOddSession()
        requests_list = [("http://x", {"n": i}) for i in range(4)]
        results = _parallel_post(requests_list, concurrency=4,
                                 tolerant=True)
        self.assertEqual([r is None for r in results],
                         [False, True, False, True])


class PostWithRetryTest(unittest.TestCase):
    def setUp(self):
        import ingest.fetchers.ackerwines as mod
        self._mod = mod
        self._sleep = mod.time.sleep
        self._new_session = mod._new_session
        self._hard_timeout = mod.HARD_TIMEOUT_S
        mod.time.sleep = lambda _s: None  # keep the test fast

    def tearDown(self):
        self._mod.time.sleep = self._sleep
        self._mod._new_session = self._new_session
        self._mod.HARD_TIMEOUT_S = self._hard_timeout

    def test_retries_then_succeeds_after_transient_failures(self):
        """Confirmed real: a single request can stall for minutes with 0
        bytes received despite an explicit timeout -- one such stall must
        not kill the whole (thousands-of-requests) discover() sweep."""
        from ingest.fetchers.ackerwines import _post_with_retry

        class FakeResp:
            status_code = 200

        calls = {"n": 0}

        class FlakySession:
            def post(self, url, json, headers, timeout):
                calls["n"] += 1
                if calls["n"] < 3:
                    raise TimeoutError("stalled")
                return FakeResp()

        self._mod._new_session = lambda: FlakySession()
        resp = _post_with_retry("http://x", {}, attempts=3)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calls["n"], 3)

    def test_transient_http_error_is_retried_not_silently_ok(self):
        """Confirmed real gap: a 5xx/429 response doesn't raise, so it used
        to be treated as "ok" and never retried -- discover() would then
        silently coerce it to totalLots=0, indistinguishable from a
        genuine empty id, dropping a real auction with no retry/log."""
        from ingest.fetchers.ackerwines import _post_with_retry

        class FakeResp:
            def __init__(self, status_code):
                self.status_code = status_code

        calls = {"n": 0}

        class FlakyHttpSession:
            def post(self, url, json, headers, timeout):
                calls["n"] += 1
                if calls["n"] < 3:
                    return FakeResp(503)
                return FakeResp(200)

        self._mod._new_session = lambda: FlakyHttpSession()
        resp = _post_with_retry("http://x", {}, attempts=3)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(calls["n"], 3)

    def test_reraises_once_all_attempts_exhausted(self):
        """Confirmed real: orchestrate.py's per-ref loop only catches
        RuntimeError (the shared fetcher contract every other fetcher's
        own raises already follow) -- re-raising last_exc's own type
        bypassed that catch, aborting the whole provider run instead of
        skipping just this one ref."""
        from ingest.fetchers.ackerwines import _post_with_retry

        class AlwaysFailsSession:
            def post(self, url, json, headers, timeout):
                raise TimeoutError("stalled")

        self._mod._new_session = lambda: AlwaysFailsSession()
        with self.assertRaises(RuntimeError) as ctx:
            _post_with_retry("http://x", {}, attempts=3)
        self.assertIsInstance(ctx.exception.__cause__, TimeoutError)

    def test_hard_watchdog_abandons_a_call_curl_never_returns_from(self):
        """Confirmed real (2026-11-03): a production run wedged for 7+
        hours inside a single curl call that never raised despite
        timeout=30 -- the hard watchdog must bound even a call that never
        returns at all, not just one that raises late."""
        import threading

        from ingest.fetchers.ackerwines import _post_with_retry

        self._mod.HARD_TIMEOUT_S = 0.05

        class NeverReturnsSession:
            def post(self, url, json, headers, timeout):
                threading.Event().wait()  # blocks forever, like the stuck curl call

        self._mod._new_session = lambda: NeverReturnsSession()
        with self.assertRaises(RuntimeError):
            _post_with_retry("http://x", {}, attempts=2)


if __name__ == "__main__":
    unittest.main()
