import unittest
from unittest import mock

from ingest.fetchers.sylvies import SylviesFetcher

ENDED_AUCTIONS_HTML = (
    '<a href="/en/auction/145">a</a>'
    '<a href="/en/auction/253">b</a>'
    '<a href="/en/auction/145">dup</a>')

LOT_PAGE_SINGLE = """
<title> All lots in the auction of 3 &amp; 4 February 2012 </title>
<div class="auction_item">
    <p class="lot_nr"><a href="/en/auction/145/lot/73211">1</a></p>
    <div class="lot_item lot_wine_73211">
        <div class="lot_name"><a href="#">1983 Château Palmer</a></div>
        <div class="lot_description">Margaux | Mc</div>
        <div class="lot_bottle">14 Bottle(s)</div>
        <div class="lot_bottle_type">4 neck</div>
    </div>
    <div>
        <div class="lot_estimate">Estimate</div>
        <p>&euro; 2600 - &euro; 3600</p>
    </div>
    <div>
        <div class="lot_my_bid">Result</div>
        <p>&euro; 2500</p>
    </div>
</div>
"""

LOT_PAGE_UNSOLD = """
<title> All lots in the auction of 3 &amp; 4 February 2012 </title>
<div class="auction_item">
    <p class="lot_nr"><a href="#">2</a></p>
    <div class="lot_item lot_wine_1">
        <div class="lot_name"><a href="#">1990 Some Wine</a></div>
    </div>
    <div>
        <div class="lot_my_bid">Result</div>
        This lot has not been sold.
    </div>
</div>
"""


class FakeResponse:
    def __init__(self, text):
        self.text = text


class FakeSession:
    def __init__(self, pages):
        self.pages = pages
        self.cookies = _CookieJar()
        self.requests = []

    def get(self, url):
        self.requests.append(url)
        for key, text in self.pages.items():
            if key in url:
                return FakeResponse(text)
        return FakeResponse("")


LOGIN_PAGE_HTML = "<title>Login to Sylvie's online wine auctions</title>"


class _CookieJar:
    def __init__(self):
        self._store = {}

    def set(self, name, value, **kwargs):  # pylint: disable=unused-argument
        self._store[name] = value

    def get(self, name):
        return self._store.get(name)


class TestSylvies(unittest.TestCase):
    def test_auth_sets_login_cookies(self):
        f = SylviesFetcher()
        session = FakeSession({})
        env = {"SYLVIES_USER": "u", "SYLVIES_PWD": "p"}
        with mock.patch("ingest.fetchers.sylvies.sylvies_login",
                        return_value={".ASPXAUTH": "tok",
                                     "afd_azwaf_jsclearance": "clr"}):
            self.assertTrue(f.auth(session, env))
        self.assertEqual(session.cookies.get(".ASPXAUTH"), "tok")
        self.assertEqual(session.cookies.get("afd_azwaf_jsclearance"), "clr")

    def test_auth_fails_without_credentials(self):
        f = SylviesFetcher()
        self.assertFalse(f.auth(FakeSession({}), {}))

    def test_discover_dedupes_auction_ids(self):
        f = SylviesFetcher()
        refs = f.discover(FakeSession({"ended-auctions": ENDED_AUCTIONS_HTML}))
        self.assertEqual([r.auction_id for r in refs], ["145", "253"])

    def test_fetch_single_lot(self):
        """Confirmed real case: a single-wine lot (auction 145, lot 1)."""
        f = SylviesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("sylvies", "145",
                         url="https://www.sylvies.be/en/auction/145")
        session = FakeSession({"page=1": LOT_PAGE_SINGLE, "page=2": ""})
        result = f.fetch(session, ref)
        self.assertEqual(result.data["auction"]["name"],
                         "All lots in the auction of 3 & 4 February 2012")
        lots = result.data["lots"]
        self.assertEqual(len(lots), 1)
        self.assertEqual(lots[0]["lot_no"], "1")
        self.assertEqual(lots[0]["subs"][0]["name"], "1983 Château Palmer")
        self.assertEqual(lots[0]["estimate_text"], "€ 2600 - € 3600")
        self.assertEqual(lots[0]["result_text"], "€ 2500")

    def test_get_relogins_once_on_expired_session(self):
        """Confirmed real case: the login/WAF cookies expire after
        ~30 minutes (checked their own "expires" attribute right after
        a fresh login), far shorter than a full ingest run -- the
        server then silently serves the login page instead of an
        error. A single expired-mid-fetch must trigger exactly one
        re-login, then succeed."""
        f = SylviesFetcher()
        f._credentials = ("u", "p", True)
        calls = {"n": 0}

        def fake_get(url):
            calls["n"] += 1
            if calls["n"] == 1:
                return FakeResponse(LOGIN_PAGE_HTML)
            return FakeResponse("real content")

        session = mock.Mock()
        session.get.side_effect = fake_get
        with mock.patch.object(SylviesFetcher, "_login", return_value=True):
            text = f._get(session, "https://www.sylvies.be/en/auction/1")
        self.assertEqual(text, "real content")
        self.assertEqual(calls["n"], 2)

    def test_get_raises_without_credentials_on_expired_session(self):
        f = SylviesFetcher()
        session = mock.Mock()
        session.get.return_value = FakeResponse(LOGIN_PAGE_HTML)
        with self.assertRaises(RuntimeError):
            f._get(session, "https://www.sylvies.be/en/auction/1")

    def test_fetch_relogins_on_empty_first_page(self):
        """Confirmed real case: the separate Azure WAF clearance cookie
        expires faster than the .ASPXAUTH login cookie _get() already
        detects -- the server then serves its WAF JS-challenge page
        (no "Login to Sylvie" text) instead, which looks like a
        legitimate "0 lots" result unless treated as always-suspicious
        on page 1."""
        f = SylviesFetcher()
        f._credentials = ("u", "p", True)
        from ingest.models import AuctionRef
        ref = AuctionRef("sylvies", "145",
                         url="https://www.sylvies.be/en/auction/145")
        calls = {"n": 0}

        def fake_get(url):
            calls["n"] += 1
            if "page=1" in url and calls["n"] == 1:
                return FakeResponse("<title>WAF challenge</title>")
            if "page=1" in url:
                return FakeResponse(LOT_PAGE_SINGLE)
            return FakeResponse("")

        session = mock.Mock()
        session.get.side_effect = fake_get
        with mock.patch.object(SylviesFetcher, "_login", return_value=True):
            result = f.fetch(session, ref)
        self.assertEqual(len(result.data["lots"]), 1)

    def test_fetch_unsold_lot_has_no_result_p_tag(self):
        """Confirmed real case: an unsold lot's "Result" div has no <p>
        at all, just a bare "This lot has not been sold." text node --
        must not be read as a price."""
        f = SylviesFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("sylvies", "145",
                         url="https://www.sylvies.be/en/auction/145")
        session = FakeSession({"page=1": LOT_PAGE_UNSOLD, "page=2": ""})
        result = f.fetch(session, ref)
        lot = result.data["lots"][0]
        self.assertIn("not been sold", lot["result_text"])


if __name__ == "__main__":
    unittest.main()
