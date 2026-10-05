"""Fetcher for Pandolfini auction results (server-rendered, login required).

Pandolfini requires a logged-in session (``codiceutente_pandolfini`` cookie)
to reveal results; the results are server-side rendered with the lots embedded
as JSON-LD (``ItemList``).

- discover: parse ``/uk/departments/fine-and-collectible-wines.asp`` for
  ``/uk/auction-{id}/{slug}.asp`` links.
- fetch: load the auction page and extract the JSON-LD ``SaleEvent`` (meta)
  and ``ItemList`` (lots: ``name``, ``offers.price`` = sold price incl.
  buyer's premium, ``offers.priceCurrency``, ``availability``).
"""
import json
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.pandolfini.it"
LOGIN_PAGE = f"{BASE_URL}/uk/my-panel/index.asp"
LOGIN_URL = f"{BASE_URL}/uk/controller.asp?action=community-login"


class PandolfiniFetcher:
    provider = "pandolfini"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def auth(self, session, env):
        """Log in with ``PANDOLFINI_USER``/``PANDOLFINI_PWD``.

        Sets the ``codiceutente_pandolfini`` session cookie. Returns True on
        success.
        """
        user = env.get("PANDOLFINI_USER")
        password = env.get("PANDOLFINI_PWD")
        if not user or not password:
            return False
        session.get(LOGIN_PAGE)
        session.post(
            LOGIN_URL,
            data={"usr": user, "psw": password, "remember": "checked",
                  "formName": "userPanel",
                  "_success": f"{self.base_url}/uk/my-panel/index.asp"},
            headers={"Referer": LOGIN_PAGE, "Origin": self.base_url},
        )
        return bool(session.cookies.get("codiceutente_pandolfini"))

    def discover(self, session):
        html = session.get(
            f"{self.base_url}/uk/departments/"
            "fine-and-collectible-wines.asp").text
        refs = []
        seen = set()
        for match in re.finditer(r'/uk/auction-(\d+)/([a-z0-9\-]+)\.asp',
                                 html):
            aid = match.group(1)
            if aid in seen:
                continue
            seen.add(aid)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=aid,
                url=(f"{self.base_url}/uk/auction-{aid}/"
                     f"{match.group(2)}.asp?action=reset"),
            ))
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        meta, lots = self._extract(html)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"provider": self.provider,
                  "auction_id": ref.auction_id,
                  "auction": meta,
                  "lots": lots},
        )

    @staticmethod
    def _extract(html):
        meta = {}
        lots = []
        for block in re.finditer(
                r'<script type="application/ld\+json">(.*?)</script>',
                html, re.S):
            data = re.sub(r"[\x00-\x1f]", " ", block.group(1))
            try:
                doc = json.loads(data)
            except (ValueError, TypeError):
                continue
            for entry in doc.get("@graph", []):
                etype = entry.get("@type")
                if etype == "SaleEvent":
                    location = entry.get("location") or {}
                    meta = {
                        "name": entry.get("name"),
                        "start_date": entry.get("startDate"),
                        "location": location.get("name"),
                    }
                elif etype == "ItemList":
                    for item in entry.get("itemListElement", []):
                        product = item.get("item", {})
                        offers = product.get("offers", {})
                        lots.append({
                            "name": (product.get("name") or "").strip(),
                            "price": offers.get("price"),
                            "currency": offers.get("priceCurrency"),
                            "sold": str(offers.get("availability", ""))
                            .endswith("SoldOut"),
                            "url": offers.get("url") or item.get("url"),
                        })
        return meta, lots
