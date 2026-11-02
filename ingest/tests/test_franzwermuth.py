import unittest

from ingest.fetchers.franzwermuth import FranzWermuthFetcher

HOME_HTML = """
<a href="Auktionen/Auktion_07.11.2026_Katalog_Coll24b.pdf">Katalog</a>
<a href="Auktionen/Ergebnisliste_Auktion_29.04.2023_Collection_17.pdf">Ergebnisliste</a>
"""

ARCHIV_HTML = """
<a href="Auktionen/Coll5_Ergebnisse.pdf">Ergebnisse</a>
<a href="Auktionen/FJWermuth_23.4.2016_Ergebnisliste.pdf">Ergebnisliste</a>
<a href="Auktionen/Ergebnisliste_Auktion_29.04.2023_Collection_17.pdf">Ergebnisliste</a>
"""


class FakeResponse:
    def __init__(self, text="", content=None, status_code=200):
        self.text = text
        self.content = content if content is not None else text.encode()
        self.status_code = status_code


class FakeSession:
    def __init__(self, pages):
        self.pages = pages

    def get(self, url):
        for key, value in self.pages.items():
            if url.endswith(key):
                return value if isinstance(value, FakeResponse) \
                    else FakeResponse(value)
        return FakeResponse("")


class TestFranzWermuth(unittest.TestCase):
    def test_discover_dedupes_across_home_and_archiv_pages(self):
        f = FranzWermuthFetcher()
        session = FakeSession({"/": HOME_HTML, "/Archiv.html": ARCHIV_HTML})
        refs = f.discover(session)
        ids = sorted(r.auction_id for r in refs)
        self.assertEqual(ids, ["17", "5"])

    def test_discover_skips_filename_with_no_collection_number(self):
        """Confirmed real case: the 2016-04-23 results file has no
        "Coll"/"Collection" number anywhere in its name -- can't be
        reliably attributed to a collection, so it's dropped rather
        than guessed."""
        f = FranzWermuthFetcher()
        session = FakeSession({
            "/": "", "/Archiv.html":
            '<a href="Auktionen/FJWermuth_23.4.2016_Ergebnisliste.pdf">'
            'Ergebnisliste</a>'})
        self.assertEqual(f.discover(session), [])

    def test_discover_ignores_catalog_links(self):
        f = FranzWermuthFetcher()
        session = FakeSession({
            "/": '<a href="Auktionen/Auktion_1.11.2025_Coll_22_Katalog'
                 '.pdf">Katalog</a>',
            "/Archiv.html": "",
        })
        self.assertEqual(f.discover(session), [])

    def test_fetch_downloads_raw_bytes(self):
        f = FranzWermuthFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("franzwermuth", "17",
                         url="https://www.franzwermuth.ch/Auktionen/"
                             "Ergebnisliste_x_Collection_17.pdf")
        session = FakeSession({})
        session.pages["Collection_17.pdf"] = FakeResponse(
            content=b"%PDF-fake")
        result = f.fetch(session, ref)
        self.assertEqual(result.content, b"%PDF-fake")
        self.assertEqual(result.filename, "live/coll17_ergebnis.pdf")

    def test_fetch_raises_on_404_instead_of_archiving_the_error_page(self):
        """Confirmed real case: Archiv.html links to a stale, typo'd
        filename for Collection 9 that 404s on the live server -- must
        not silently archive that 404 HTML page as if it were the
        results PDF."""
        f = FranzWermuthFetcher()
        from ingest.models import AuctionRef
        ref = AuctionRef("franzwermuth", "9",
                         url="https://www.franzwermuth.ch/Auktionen/"
                             "Coll9_27.4.2018_Ergebnisse.pdf")
        session = FakeSession({})
        session.pages["Ergebnisse.pdf"] = FakeResponse(
            text="<html>404 Not Found</html>", status_code=404)
        with self.assertRaises(RuntimeError):
            f.fetch(session, ref)


if __name__ == "__main__":
    unittest.main()
