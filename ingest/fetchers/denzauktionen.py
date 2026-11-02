"""Fetcher for denzauktionen.ch -- the successor site to the dead
wermuth.ch/denz.ch domains (confirmed: denz.ch now redirects to an
unrelated office-furniture company, wermuth.ch serves an expired
generic self-signed certificate from an unrelated host). Both of those
old domains were "Wermuth S.A." / Denz Weine, same auction house --
this fetcher feeds the existing "wermuth-sa" DB provider's Denz archive
folder, not a new provider (see build_db.py's load_denz_wermuth, which
already parses this exact "number-Resultate*.pdf" format for the local
archive and keeps a running WZ-catalog numbering that this site
continues, e.g. WZ-297 == "Auktion #297").

- discover: parse https://denzauktionen.ch/vergangene-auktionen/
  (static HTML, no login, no AJAX) for "Auktion #<n> vom <date>" titles
  paired with their "Resultate" PDF download link. The page only
  server-renders the newest ~4 auctions -- there's no JS-driven "Mehr
  laden" pagination here, but that's fine for ongoing automation: a new
  auction always shows up among the newest as soon as it's published.
- fetch: downloads the results PDF as raw bytes. load_denz_wermuth
  parses it directly (same PDF format/classification-by-filename the
  local archive already uses: a name containing "resultat" is a
  results file), so this fetcher does no PDF parsing itself.
"""
import re

from ..models import AuctionRef, FetchResult

BASE_URL = "https://denzauktionen.ch"

_GERMAN_MONTHS = {
    "januar": 1, "jan": 1, "februar": 2, "feb": 2, "märz": 3, "marz": 3,
    "mrz": 3, "april": 4, "apr": 4, "mai": 5, "juni": 6, "jun": 6,
    "juli": 7, "jul": 7, "august": 8, "aug": 8, "september": 9, "sept": 9,
    "sep": 9, "oktober": 10, "okt": 10, "november": 11, "nov": 11,
    "dezember": 12, "dez": 12,
}

# The tempered dot (?:(?!Auktion\s*#).)*? -- instead of a plain, unbounded
# `.*?` -- stops the match from crossing into the NEXT "Auktion #..."
# heading. With a plain `.*?`, an entry published without its own
# Resultate link yet (e.g. a just-closed auction whose PDF isn't up) would
# silently pair with the *following* (older) entry's PDF url, mislabeling
# which results file belongs to which auction number/date. With the
# tempered dot, that entry simply fails to match (and is picked up on a
# later run once its own PDF link appears) instead of stealing someone
# else's.
_ENTRY_RE = re.compile(
    r"Auktion\s*#(\d+)\s*vom\s*(\d{1,2})\.\s*(\w+)\.?\s*(\d{4})"
    r"(?:(?!Auktion\s*#).)*?href=\"([^\"]+?\.pdf)\"[^>]*>\s*Resultate",
    re.IGNORECASE | re.DOTALL)


class DenzauktionenFetcher:
    provider = "denzauktionen"

    def discover(self, session):
        html = session.get(f"{BASE_URL}/vergangene-auktionen/").text
        refs = []
        seen = set()
        for m in _ENTRY_RE.finditer(html):
            number, day, month_name, year, pdf_url = m.groups()
            if number in seen:
                continue
            seen.add(number)
            month = _GERMAN_MONTHS.get(month_name.lower())
            date = (f"{year}-{month:02d}-{int(day):02d}"
                    if month else None)
            refs.append(AuctionRef(
                provider=self.provider, auction_id=number,
                url=pdf_url, date=date or ""))
        return refs

    def fetch(self, session, ref):
        resp = session.get(ref.url)
        content = resp.content if hasattr(resp, "content") else None
        if not content:
            content = resp.text.encode("utf-8")
        ddmmyyyy = ""
        if ref.date:
            y, mo, d = ref.date.split("-")
            ddmmyyyy = f"_{d}{mo}{y}"
        # "live/" subdir: load_denz_wermuth only recurses into actual
        # subdirectories of the Denz archive root (mirroring the manual
        # archive's year folders), not files dropped directly in it.
        filename = f"live/{ref.auction_id}{ddmmyyyy}_Resultate.pdf"
        return FetchResult(
            provider=self.provider, auction_id=ref.auction_id,
            content=content, filename=filename)
