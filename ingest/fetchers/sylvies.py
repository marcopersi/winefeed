"""Fetcher for sylvies.be (login required since ~mid-2026, Azure WAF).

- auth: run the camoufox login flow (ingest/sylvies_auth.py, solves the
  Azure WAF JS challenge) and copy the resulting cookies into the
  session. Confirmed these survive on a plain requests/curl_cffi session
  for every subsequent request -- no further JS challenge, camoufox is
  only needed for this one login step.
- discover: parse ``/en/ended-auctions`` for ``/en/auction/{id}`` links
  (one page, no pagination -- confirmed empirically against the live
  site, 98 auctions, ids 141-253+).
- fetch: paginate ``/en/auction/{id}?sort=lotnr_asc&page={n}`` (25
  items/page) until a page returns no ``auction_item`` blocks. Each
  item can hold more than one ``lot_item`` sub-div -- a real mixed lot
  (several distinct wines sharing one lot number), not a scrape
  artifact; the historic txt-captured archive's scraper only ever read
  the first one (see build_db.py's module note on load_sylvies_txt),
  this fetcher reads all of them, same as load_sylvies_html already
  does for its one HTML-archived period.
"""
import re
from html import unescape

from bs4 import BeautifulSoup

from ..models import AuctionRef, FetchResult
from ..sylvies_auth import login as sylvies_login

BASE_URL = "https://www.sylvies.be"
PAGE_SIZE = 25


_LOGIN_PAGE_TITLE = "Login to Sylvie"


class SylviesFetcher:
    provider = "sylvies"

    def __init__(self):
        self._credentials = None

    def auth(self, session, env):
        user = env.get("SYLVIES_USER")
        password = env.get("SYLVIES_PWD")
        if not user or not password:
            return False
        headless = env.get("SYLVIES_HEADLESS", "1") != "0"
        if not self._login(session, user, password, headless):
            return False
        self._credentials = (user, password, headless)
        return True

    @staticmethod
    def _login(session, user, password, headless):
        cookies = sylvies_login(user, password, headless=headless)
        if not cookies:
            return False
        for name, value in cookies.items():
            session.cookies.set(name, value, domain=".sylvies.be")
        return True

    def discover(self, session):
        html = session.get(f"{BASE_URL}/en/ended-auctions").text
        refs = []
        seen = set()
        for aid in re.findall(r'/en/auction/(\d+)"', html):
            if aid in seen:
                continue
            seen.add(aid)
            refs.append(AuctionRef(
                provider=self.provider, auction_id=aid,
                url=f"{BASE_URL}/en/auction/{aid}"))
        return refs

    def fetch(self, session, ref):
        title = None
        lots = []
        page = 1
        retried_empty_first_page = False
        while True:
            url = (f"{BASE_URL}/en/auction/{ref.auction_id}"
                   f"?sort=lotnr_asc&page={page}")
            html = self._get(session, url)
            if title is None:
                m = re.search(r"<title>\s*([^<]*?)\s*</title>", html)
                title = unescape(m.group(1)) if m else None
            soup = BeautifulSoup(html, "html.parser")
            items = soup.find_all("div", class_="auction_item")
            if not items:
                # Confirmed real case: every auction_id discover() returns
                # is an ended auction with real lots -- an empty page 1 is
                # never legitimate. It silently happens when the separate
                # Azure WAF "clearance" cookie expires (shorter-lived than
                # and independent from the .ASPXAUTH login cookie _get()
                # already checks for): the server then serves its WAF JS
                # challenge page instead of a login page, which doesn't
                # contain "Login to Sylvie" and so isn't caught there --
                # it just looks like "0 lots" to this loop. One forced
                # re-login (which re-solves the WAF challenge via
                # camoufox) and retry of page 1 covers that case too.
                if (page == 1 and not retried_empty_first_page
                        and self._credentials
                        and self._login(session, *self._credentials)):
                    retried_empty_first_page = True
                    title = None
                    continue
                break
            for item in items:
                lot = _map_item(item)
                if lot:
                    lots.append(lot)
            page += 1

        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={
                "auction": {"id": ref.auction_id, "name": title,
                           "date": None},
                "lots": lots,
            },
        )

    def _get(self, session, url):
        """GET with one automatic re-login retry.

        Confirmed real case: the login/WAF-clearance cookies carry a
        ~30-minute expiry (checked the cookies' own "expires" attribute
        right after a fresh login), far shorter than a full ingest run
        (98 auctions, some 150+ pages each -- hours, not minutes). Once
        expired, the server silently serves the login page instead of
        an error, which would otherwise look exactly like "0 lots on
        this auction" to the caller and cut every remaining auction's
        data short without any error raised.
        """
        text = session.get(url).text
        if _LOGIN_PAGE_TITLE not in text:
            return text
        if not self._credentials:
            raise RuntimeError(
                "sylvies session expired and no credentials to re-login")
        if not self._login(session, *self._credentials):
            raise RuntimeError("sylvies re-login failed")
        return session.get(url).text


def _map_item(item):
    """Raw text per field, same structure build_db.py's
    _sylvies_build_lot_row expects -- the actual vintage/description/
    bottle/estimate/result parsing lives there (shared with
    load_sylvies_html), not duplicated here."""
    lot_nr_el = item.find("p", class_="lot_nr")
    lot_no = lot_nr_el.get_text(strip=True) if lot_nr_el else None
    if not lot_no:
        return None

    subs = []
    for li in item.find_all(
            "div", class_=lambda c: c and c.startswith("lot_item")):
        name_el = li.find("div", class_="lot_name")
        desc_el = li.find("div", class_="lot_description")
        bottle_el = li.find("div", class_="lot_bottle")
        bt_el = li.find("div", class_="lot_bottle_type")
        subs.append({
            "name": name_el.get_text(strip=True) if name_el else None,
            "description": desc_el.get_text(strip=True) if desc_el else None,
            "bottle": bottle_el.get_text(strip=True) if bottle_el else None,
            "bottle_type": bt_el.get_text(strip=True) if bt_el else None,
        })

    est_el = item.find("div", class_="lot_estimate")
    estimate_text = None
    if est_el:
        p = est_el.find_next_sibling("p")
        if p:
            estimate_text = p.get_text(strip=True)

    bid_el = item.find("div", class_="lot_my_bid")
    result_text = None
    if bid_el and bid_el.parent:
        # Confirmed real case: an unsold lot has no <p> at all, just a
        # bare "This lot has not been sold." text node right after this
        # div inside the same parent -- read the whole parent's text,
        # not find_next("p"), which would run past it into other lots.
        result_text = re.sub(r"^\s*Result\s*", "",
                              bid_el.parent.get_text(strip=True),
                              flags=re.IGNORECASE)

    return {
        "lot_no": lot_no,
        "subs": subs,
        "estimate_text": estimate_text,
        "result_text": result_text,
    }
