"""Fetcher for Finarte auction results (login required).

- auth: POST ``finarte-login.php`` with ``signin-email``/``signin-password``;
  the returned PHP session then reveals results on the auction pages.
- discover: parse the wine past-auctions listing for ``/auction/{slug}`` links.
- fetch: load the auction page and extract the inline lots (``prezzo di
  aggiudicazione`` = hammer incl. buyer's premium, ``base_asta`` = start,
  ``stima`` = estimate, ``anno`` = vintage).
"""
import json
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.finarte.it"
LOGIN_URL = ("https://www.finarte.it/wp-content/themes/finarte2020/assets/"
             "ajax/finarte-login.php")


class FinarteFetcher:
    provider = "finarte"

    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url.rstrip("/")

    def auth(self, session, env):
        user = env.get("FINARTE_USER")
        password = env.get("FINARTE_PWD")
        if not user or not password:
            return False
        resp = session.post(
            LOGIN_URL,
            json={"signin-email": user, "signin-password": password},
            headers={"X-Requested-With": "XMLHttpRequest",
                     "Origin": self.base_url},
        )
        return '"success":true' in resp.text

    def discover(self, session):
        html = session.get(
            f"{self.base_url}/auctions/past-auctions/"
            "?lang=en&dip=DPT_Vini&ARCHIVIATA=T").text
        refs = []
        seen = set()
        for match in re.finditer(r'href="(/auction/[a-z0-9\-]+)"', html):
            slug = match.group(1)
            if slug in seen:
                continue
            seen.add(slug)
            refs.append(AuctionRef(
                provider=self.provider,
                auction_id=slug.rsplit("-", 1)[-1],
                url=self.base_url + slug,
            ))
        return refs

    def fetch(self, session, ref):
        html = session.get(ref.url).text
        slug = re.search(r"/auction/([a-z0-9\-]+)", ref.url)
        return FetchResult(
            provider=self.provider,
            auction_id=ref.auction_id,
            data={"auction": {"slug": slug.group(1) if slug else None,
                              "name": None, "date": None},
                  "lots": [self._map_lot(lot)
                           for lot in self._extract_lots(html)]},
        )

    @staticmethod
    def _extract_lots(html):
        marker = html.find('id="__DATI_LOTTI__"')
        if marker == -1:
            return []
        start = html.find("[", marker)
        end = html.find("</script>", start)
        try:
            return json.loads(html[start:end])
        except (ValueError, TypeError):
            return []

    @staticmethod
    def _map_lot(lot):
        sold = lot.get("opera_venduta") == "True" \
            or lot.get("stato") == "VENDUTO"
        return {
            "lot_nr": lot.get("numero_lotto"),
            "name": lot.get("stringa_filtro_autore_lotto"),
            "region": lot.get("stringa_categoria_lotto"),
            "vintage": lot.get("anno"),
            "estimate_min": lot.get("valore_min"),
            "estimate_max": lot.get("valore_max"),
            "hammer_price": lot.get("prezzo_aggiudicazione"),
            "sold": 1 if sold else 0,
            "currency": "EUR",
            "vat_regime": lot.get("regime_vendita"),
        }
