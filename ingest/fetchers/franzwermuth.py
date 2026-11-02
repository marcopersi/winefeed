"""Fetcher for franzwermuth.ch (Dr. Spengler & Partner AG / Franz J.
Wermuth Weinauktionen, Zurich) -- a separate, still fully active auction
house from "Wermuth S.A." / Denz Weine (confirmed by the user: distinct
company, own provider/loader).

- discover: the site's own "Archiv.html" page hasn't been updated since
  2023 (stops at Collection 17); the newest 2-3 collections' links only
  ever show up on the HOMEPAGE. Both pages are scanned for any href
  under "Auktionen/" whose filename contains "ergebnis"/"Ergebnis" --
  confirmed real: a catalog PDF is always labelled "Katalog", a results
  file always has "Ergebnis"/"Ergebnisliste"/"Ergebnisse" in its name
  (even though the rest of the filename convention has drifted through
  at least four different shapes over the years). The collection number
  is pulled from the filename via "Coll(ection)?_?<n>" -- present in
  every results filename except one 2016 historical outlier, which is
  silently skipped (no reliable way to recover its number from the
  filename alone, and it's not a going-forward concern).
- fetch: downloads the raw file (PDF, or an old-style binary .xls for
  the rare case a results file ever uses that format) -- parsing lives
  in build_db.py's load_franzwermuth, not here.

Confirmed real gap: Collections 18-23 (Nov 2023 - Apr 2026) have no
findable results file anywhere on the site right now -- their catalog
PDFs/xls are linked, but checked carefully (full PDF text, not just
the first page) and no lot-by-lot result table is present. Left
unresolved, same kind of redesign/posting-lag gap as koppe's 2025 hole.
"""
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.franzwermuth.ch"
PAGES = ("/", "/Archiv.html")

_RESULT_LINK_RE = re.compile(
    r'href="(Auktionen/[^"]*?[Ee]rgebnis[^"]*?\.(?:pdf|xlsx?))"')
_COLL_NUM_RE = re.compile(r"[Cc]oll(?:ection)?_?(\d+)")


class FranzWermuthFetcher:
    provider = "franzwermuth"

    def discover(self, session):
        refs = []
        seen = set()
        for path in PAGES:
            html = session.get(f"{BASE_URL}{path}").text
            for m in _RESULT_LINK_RE.finditer(html):
                rel_url = m.group(1)
                num_m = _COLL_NUM_RE.search(rel_url)
                if not num_m:
                    continue
                coll = num_m.group(1)
                if coll in seen:
                    continue
                seen.add(coll)
                refs.append(AuctionRef(
                    provider=self.provider, auction_id=coll,
                    url=f"{BASE_URL}/{rel_url}"))
        return refs

    def fetch(self, session, ref):
        resp = session.get(ref.url)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            # Confirmed real case: Archiv.html links to
            # "Coll9_27.4.2018_Ergebnisse.pdf" (collection 9, really
            # 27.4.2019 per its own title -- a stale typo'd filename),
            # which 404s on the live server. Raising here (instead of
            # silently archiving the 404 HTML page as if it were a
            # PDF) lets orchestrate.py's RuntimeError handling skip it
            # and retry on a later run instead of poisoning the archive.
            raise RuntimeError(
                f"franzwermuth/{ref.auction_id}: HTTP {status} for "
                f"{ref.url}")
        content = getattr(resp, "content", None) or resp.text.encode("utf-8")
        ext = ref.url.rsplit(".", 1)[-1].lower()
        return FetchResult(
            provider=self.provider, auction_id=ref.auction_id,
            content=content,
            filename=f"live/coll{ref.auction_id}_ergebnis.{ext}")
