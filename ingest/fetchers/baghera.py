"""Fetcher for bagherawines.auction.

No login needed anywhere in this path -- the results PDFs are served
publicly with no auth (confirmed via direct, unauthenticated request: HTTP
200, content-type application/pdf). An earlier investigation found no
lot-level price data behind login anywhere on the site; that was looking
at the wrong part of the site -- this results-PDF archive was never
covered by it, and BAGHERA_USER/BAGHERA_PWD (already in .env_local) turn
out to be unused by this fetcher.

- discover: GET /fr/catalogue/archive, a single static HTML page listing
  every past (and some future/unresolved) sale as a "catalogue/voir/{id}"
  link -- 173 ids as of 2026-11, going back to id 1. Only 29 of those were
  ever previously captured (the "named" icon sales: Henri Jayer, DRC, the
  Kipling# series, ...), via a now-lost ad-hoc script. Checked all 144
  remaining ids individually (Nov 2026): NONE currently has a results PDF
  linked -- not just the recurring "Wine o'clock" series, but also real
  gaps inside the Kipling# series itself (e.g. #6, id 106). This matches
  the 29 already captured almost exactly, so there is no silent backlog
  being missed; the site itself only ever publishes a results PDF for a
  minority of its sales.
- fetch: GET the auction's own "catalogue/voir/{id}" detail page and look
  for the one link under "assets/uploads/bilan/catalogues/{id}/...pdf" --
  that is the one and only results PDF. Confirmed real: the filename
  itself follows no fixed convention across sales (e.g.
  "..._Sale_Results.pdf" vs "sale_Kipling9-report.pdf" vs
  "results_-_i_wine_a_dream.pdf"), so it must be read off the detail page,
  never constructed from the id alone. Not every listed sale ever gets
  one (see above) -- those ids simply raise (never marked fetched) and
  get retried on the next run, since there's no reliable way to tell "not
  published yet" from "never will be".
  The detail page's own sale date (always shown in French, "DD month
  YYYY HH:MM", regardless of the PDF's own language) is embedded into the
  downloaded file's name so build_db.py's load_baghera doesn't need a
  second fetch to learn it (same trick as denzauktionen.py).
- Parsing (row format, hammer/premium split, "Unsold" markers, ...) lives
  in build_db.py's load_baghera, not here -- this module only acquires
  raw bytes.
"""
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://www.bagherawines.auction"
ARCHIVE_URL = f"{BASE_URL}/fr/catalogue/archive"

_VOIR_RE = re.compile(r"catalogue/voir/(\d+)")
_PDF_RE = re.compile(
    r'href="(https://www\.bagherawines\.auction/assets/uploads/bilan/'
    r'catalogues/(\d+)/[^"]+\.pdf)"', re.IGNORECASE)
_DATE_RE = re.compile(
    r"(\d{1,2})\s+(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|"
    r"ao[uû]t|septembre|octobre|novembre|d[ée]cembre)\s+(\d{4})",
    re.IGNORECASE)
_FRENCH_MONTHS = {
    "janvier": 1, "fevrier": 2, "février": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "aout": 8, "août": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "decembre": 12,
    "décembre": 12,
}


class BagheraFetcher:
    provider = "baghera"

    def discover(self, session):
        html = session.get(ARCHIVE_URL).text
        ids = sorted(set(int(m.group(1)) for m in _VOIR_RE.finditer(html)))
        return [
            AuctionRef(provider=self.provider, auction_id=str(i),
                       url=f"{BASE_URL}/fr/catalogue/voir/{i}")
            for i in ids
        ]

    def fetch(self, session, ref):
        resp = session.get(ref.url)
        status = getattr(resp, "status_code", 200)
        if status != 200:
            raise RuntimeError(
                f"baghera/{ref.auction_id}: HTTP {status} for {ref.url}")
        html = resp.text
        pdf_url = None
        for m in _PDF_RE.finditer(html):
            if m.group(2) == ref.auction_id:
                pdf_url = m.group(1)
                break
        if pdf_url is None:
            raise RuntimeError(
                f"baghera/{ref.auction_id}: no results PDF published yet")

        date_tag = ""
        date_m = _DATE_RE.search(html)
        if date_m:
            day, month_name, year = date_m.groups()
            month = _FRENCH_MONTHS.get(month_name.lower())
            if month:
                date_tag = f"_{year}{month:02d}{int(day):02d}"

        pdf_resp = session.get(pdf_url)
        pdf_status = getattr(pdf_resp, "status_code", 200)
        if pdf_status != 200:
            raise RuntimeError(
                f"baghera/{ref.auction_id}: HTTP {pdf_status} for {pdf_url}")
        content = getattr(pdf_resp, "content", None)
        if not content:
            content = pdf_resp.text.encode("utf-8")
        return FetchResult(
            provider=self.provider, auction_id=ref.auction_id,
            content=content,
            filename=f"live/{ref.auction_id}{date_tag}_results.pdf")
