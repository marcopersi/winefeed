#!/usr/bin/env python3
"""One-time OCR extraction of priceData/import/steinfels/source/2002/318.pdf.

318.pdf has no usable text layer (pdfplumber reports 3060 vector curves and
181 rects per page but only ~170 real chars -- the header). The wine table
itself is drawn as outlined glyphs, so it must be rendered to an image and
OCR'd, unlike 315/316/319/320-324 (plain text PDFs already covered by
priceData/import/steinfels/prepared/**/results_*.xlsx) and 317 (OCR'd once
by hand into wines_final.txt, see archive/priceData-parser/src/steinfels/2002/317).

Line grammar matches the other 2002/2003 catalogs (see
archive/priceData-parser/src/steinfels/2003/320/parser_320.py):
    <lot> <product/region/classification text> <qty> <unit> [OHK] <year> <price>

Known OCR confusions in this PDF's font, found by comparing rendered pages
against the raw OCR output (tesseract 5.5.1, --psm 6):
  - digit '1' before Flasche/Flaschen/Magnum/... misreads as ']' or 'l'
  - '1er' misreads as 'ler'
  - a price of '0' misreads as a short bracket-bearing token ('6)', '(6)',
    '[6)', 'fe)', '0)', ...) -- never a real price, since a real price is a
    bare digit string with optional apostrophe thousands separators.
  - 'Chateau'/'Château' loses its accent or gets a stray letter ('Chdteau')

Output: results_318.xlsx with the same column schema as results_320.xlsx
(Lot, Wine, Producer, Region, Classification, Quantity, Unit, OHK, Year,
Price_CHF, Raw_Line, Line_Number), written to
priceData/import/steinfels/prepared/2002/ so the existing load_steinfels()
glob loader in build_db.py picks it up with no code changes.
"""
import os
import re
import subprocess
import sys
import tempfile

import openpyxl

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDF_PATH = os.path.join(REPO, "priceData", "import", "steinfels", "source",
                         "2002", "318.pdf")
OUT_PATH = os.path.join(REPO, "priceData", "import", "steinfels", "prepared",
                         "2002", "results_318.xlsx")

# Same reference lists as SteinfelsParser320 (base_parser.py + parser_320.py),
# copied inline to avoid that module's dead supabase/dotenv dependency.
WINE_REGIONS = [
    'Côtes de Bordeaux', 'Lussac-St-Emilion', 'Pomerol', 'Saint Emilion', 'Saint-Emilion',
    'Haut Médoc', 'Haut-Médoc', 'Sauternes', 'Margaux', 'Pauillac', 'Pessac Léognan',
    'Pessac-Léognan', 'Saint Julien', 'Saint-Julien', 'Moulis en Médoc',
    'Moulis-en-Médoc', 'Côtes de Castillon', 'Saint Estéphe', 'Saint-Estéphe', 'Graves',
    'Lussac-St.Emilion', 'Lussac St Emilion', 'Puisseguin St Emilion', 'Listrac-Médoc',
    'Listrac', 'Bordeaux', 'Canon Fronsac', 'Premières Côtes de Blaye',
    'Bordeaux Supérieur', 'Côtes de Bourg', 'Listrac Cru Bourgeois',
    'Leroy', 'Bourgogne', 'Rhône', 'Sicilia', 'Columbia', 'Piemont',
    'Toskana', 'Priorat', 'Ribera del Duero', 'Lazio', 'Saint-Estèphe',
    'Saint Estèphe', 'Haut Mèdoc', 'Premières Côtes de Bordeaux',
    'Hospice de Beaune', 'St-Emilion',
    'Haut-Mé', 'Pauill', 'St-Em', 'St-Jul', 'Pessac-Léo',
]
REGION_MAPPINGS = {
    'Haut-Mé': 'Haut-Médoc', 'Pauill': 'Pauillac', 'St-Em': 'Saint-Emilion',
    'St-Jul': 'Saint-Julien', 'Pessac-Léo': 'Pessac-Léognan',
    'Saint-Emilio': 'Saint-Emilion',
}
WINE_PRODUCERS = [
    'Marchese Antinori', 'Marchesi Antinori', "Tenuta dell'Ornellaia",
    'Andrea Costanti', 'Tenuta San Guido', 'Castello di Ama',
    'Verbenna', 'La Torre', 'Cantina Falesco', 'Duca di Salaparuta',
    'Bodegas Palacios', 'Gentaz-Vernieux', 'Guigal', 'Chapoutier',
    'Domaine J-L. Chave', 'Paul Jaboulet Aîné', 'Henri Bonneau',
    'Château Rayas', 'Château de Beauc', 'Château de Bea', 'Domaine de Vallouit',
    'Domaine de Pegaü', 'Louis Jadot', 'Pio Cesare', 'Bruno Giacosa',
    'Mondavi/Rothschild', 'Frescobaldi/Mondavi',
    'Mondavi', 'Moët et Chandon', 'Cathérine Moine Père & Fils',
    'Domaine Romanée Conti', 'Armand Rousseau', 'Dom.du Château de Meursault',
    'P.Naudin-Varrault', 'Hubert Didier', 'Arthur Barolet',
    'Labaume Ainé & Fils', 'Zibetti', 'Raoul Clerget',
    'Domaine Chantal Lescure', 'Domaine Comte de Vogüé', 'Vincent Girardin',
    'Mahler', 'Moine Père & Fils', 'Domaine Comte Senard',
    'Royé-Labaume & Cie', 'Leroy', 'Château Sainte Michelle',
    'Antinori', 'Domaine Saier',
    'Collection Dr. Barolet', 'Bouchard Âiné & Fils', 'Paul Bouchard & Cie',
    'Bouchard Père & Fils', 'Bouchard Père & Fil', 'Paul Bouchard & Ci',
    'J. Hubert-Didier', 'Michel Noëllat', 'Drouhin-Laroze', 'G. de Buyssières',
    'Etienne Sauzet', 'Jean-Marie Garnier', 'Taittinger',
    'Angelo Gaja', 'Carlo Boffa', 'Sottimano', 'Conterno Fantino',
    'Luciano Sandro', 'Scavino', 'Castello dei Rampolla', 'Dominus Estate',
    'Louis Latour', 'Comte Georges', 'Produttori del Barbaresco',
]
CLASSIFICATION_PATTERNS = [
    r'\b(Grand\s+Cru\s+Classé)\b', r'\b(Grand\s+Cru)\b', r'\b(Cru\s+Classé)\b',
    r'\b(Cru\s+Beaujolais)\b', r'\b(Cru\s+Bourgeois)\b',
    r'\b(\d+(?:er|ème)\s+Cru\s+Classé)\b', r'\b(\d+(?:er|ème)\s+Cru)\b',
    r'\b(\d+(?:er|ème))\s+(Cru\s+[AB])\b', r'\b(\d+(?:er|ème))\s+([AB])\b',
    r'\b(\d+(?:er|ème))\b', r'\b(2e\s+vin\s+de)\b',
]
CLEANUP_PATTERNS = [
    r'\b\d+(?:er|ème)\s+Cru\s+[AB]\b', r'\b\d+(?:er|ème)\s+Cru\b',
    r'\b(Cru\s+[AB])\b', r'\bCru\b', r'\b\d+(?:er|ème)\s+[AB]\b',
    r'\b\d+(?:er|ème)\b', r'\b(2e vin de)\b', r'\b(Grand Cru)\b',
    r'\b(Cru Beaujolais)\b', r'\b(Cru Bourgeois)\b', r'\([^)]*\)',
    r'\bigt\b', r'\b[A-Z]\s*$',
]

# --- OCR text corrections (see module docstring) ---------------------------
_TEXT_FIXES = [
    (r'\bChdteau\b', 'Chateau'), (r'\bChGteau\b', 'Chateau'),
    (r'\bChéteau\b', 'Chateau'), (r'\bCh@teau\b', 'Chateau'),
    (r'\bChteau\b', 'Chateau'),
    (r'\bler\b', '1er'),
    (r'(\d)eme\b', r'\1ème'),
    (r'\bCHK\b', 'OHK'), (r'\bCHO\b', 'OHK'),
]


def _fix_text(line):
    for pat, repl in _TEXT_FIXES:
        line = re.sub(pat, repl, line)
    # '12'/'11' before a unit word misreads as ']2'/'1]' (a '1' lost to ']')
    line = re.sub(r'\](\d)(?=\s+(?:Flasche|Flaschen|Magnum|Doppelmagnum|'
                  r'Jéroboam)\b)', r'1\1', line)
    line = re.sub(r'(\d)\](?=\s+(?:Flasche|Flaschen|Magnum|Doppelmagnum|'
                  r'Jéroboam)\b)', r'\g<1>1', line)
    # '1' before a unit word misreads as ']' or a lone 'l'
    line = re.sub(r'(?:^|(?<=\s))[\]l](?=\s+(?:Flasche|Flaschen|Magnum)\b)',
                   '1', line)
    # OCR occasionally drops the space before a glued-on OHK/OC marker
    line = re.sub(r'(Flaschen?)(OHK|OC)\b', r'\1 \2', line)
    return line


def _fix_price_token(tok):
    """A real price is digits with optional ' thousands separators. Any
    token carrying a bracket char is a misread '0' (see docstring)."""
    if re.search(r'[\(\)\[\]]', tok):
        return '0'
    return tok


def ocr_pdf_lines(pdf_path):
    """Render every page at 300dpi and OCR it; yield cleaned text lines."""
    with tempfile.TemporaryDirectory() as tmp:
        prefix = os.path.join(tmp, "page")
        subprocess.run(["pdftoppm", "-r", "300", "-png", pdf_path, prefix],
                        check=True)
        pages = sorted(f for f in os.listdir(tmp) if f.endswith(".png"))
        for fname in pages:
            out = subprocess.run(
                ["tesseract", os.path.join(tmp, fname), "stdout",
                 "--psm", "6", "-l", "eng"],
                capture_output=True, text=True, check=True)
            for raw in out.stdout.split("\n"):
                line = _fix_text(raw.strip())
                if line:
                    yield line


def extract_classification(text):
    classifications = []
    for pattern in CLASSIFICATION_PATTERNS:
        classifications += [m.group(0)
                             for m in re.finditer(pattern, text, re.IGNORECASE)]
    return text, " ".join(classifications)


def clean_text(text):
    for pattern in CLEANUP_PATTERNS:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def extract_region(text):
    for region in sorted(WINE_REGIONS, key=len, reverse=True):
        pattern = r"\b" + re.escape(region) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            return text.strip(), REGION_MAPPINGS.get(region, region)
    return text.strip(), ""


def extract_producer(text):
    for producer in sorted(WINE_PRODUCERS, key=len, reverse=True):
        pattern = r"\b" + re.escape(producer) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)
            return text.strip(), producer
    return text.strip(), ""


def parse_line(line, line_no, errors):
    if "mixed lot" in line.lower() or len(line.strip()) < 10:
        return None
    if any(h in line.lower() for h in ("produkt", "gebiet", "menge",
                                        "steinfels weinauktionen",
                                        "ergebnisliste", "win2pdf")):
        return None

    lot_match = re.match(r"^(\d+)\s+(.+)$", line.strip())
    if not lot_match:
        return None
    lot_number, rest = lot_match.group(1), lot_match.group(2)
    # Stray '=', '~', ':' between the packaging note and the year (OCR noise
    # around that column boundary, e.g. "2x 6-er OHK =-1985") would otherwise
    # break the end-anchored year/OHK/unit matches below.
    rest = re.sub(r"\s*[=~:]+\s*", " ", rest).strip()
    # The same noise run sometimes also swallows a hyphen right after OHK/OC
    # ("OHK =-1985"); collapse that directly so the year stays end-anchored.
    rest = re.sub(r"\b(OHK|OC)\b[\s-]+(\d{4})\b", r"\1 \2", rest,
                  flags=re.IGNORECASE)

    price = 0
    price_match = re.search(r"(\S+)$", rest)
    if price_match:
        tok = _fix_price_token(price_match.group(1))
        if re.fullmatch(r"\d+(?:'\d+)*", tok):
            price = int(tok.replace("'", ""))
            rest = rest[:price_match.start()].strip()
        # else: last token isn't a price at all -- leave rest untouched
        # rather than silently eating whatever it actually is.

    # Year (Jahrgang) is blank on some source rows (confirmed on the
    # rendered page), so a missing year is not an error -- only strip it
    # when found. A 3-digit remnant with a trailing OCR bracket (a '1977'
    # that lost its last digit to a misread) can't be recovered; drop the
    # garbled token but still leave the row without a fabricated year.
    year = None
    year_match = re.search(r"(\d{4})\s*$", rest)
    if year_match:
        year = int(year_match.group(1))
        rest = rest[:year_match.start()].strip()
    else:
        lost_digit = re.search(r"\d{3}[\)\]]\s*$", rest)
        if lost_digit:
            errors.append(f"LOST_YEAR_DIGIT[{line_no}]: {line}")
            rest = rest[:lost_digit.start()].strip()

    is_ohk = False
    ohk_match = re.search(r"\b(OHK|OC)\b\s*$", rest, re.IGNORECASE)
    if ohk_match:
        is_ohk = True
        rest = rest[:ohk_match.start()].strip()

    # Original-case-packaging note ("2x 6-er" = packed as 2 six-packs, or
    # "in 1-er" = packed as a single N-pack) trails the real "<qty> Flaschen"
    # field; it's noise for our purposes, drop it so the quantity/unit regex
    # below still anchors at line end.
    rest = re.sub(r"\s+(?:\d+x|in)\s+\d+(?:-?er)?\s*$", "", rest,
                  flags=re.IGNORECASE)

    unit_match = re.search(
        r"(\d+(?:\s+\d+/\d+)?)\s+(Flasche|Flaschen|Magnum|Doppelmagnum|"
        r"Jéroboam)\s*$", rest, re.IGNORECASE)
    if not unit_match:
        errors.append(f"NO_UNIT[{line_no}]: {line}")
        return None
    quantity_str, unit = unit_match.group(1), unit_match.group(2)
    quantity = int(quantity_str.split()[0])
    rest = rest[:unit_match.start()].strip()

    rest, classification = extract_classification(rest)
    rest = clean_text(rest)
    rest, region = extract_region(rest)
    rest, producer = extract_producer(rest)
    wine_name = rest.strip()

    if "/" in quantity_str:
        num, den = (int(x) for x in quantity_str.split()[1].split("/"))
        unit_dl = (num / den) * 10
    elif unit.lower() == "magnum":
        unit_dl = 15.0
    elif unit.lower() in ("doppelmagnum", "jéroboam"):
        unit_dl = 30.0
    else:
        unit_dl = 7.5

    return {
        "Lot": lot_number, "Wine": wine_name, "Producer": producer,
        "Region": region, "Classification": classification,
        "Quantity": quantity, "Unit": unit_dl,
        "OHK": "Yes" if is_ohk else "No", "Year": year,
        "Price_CHF": price, "Raw_Line": line.strip(), "Line_Number": line_no,
    }


def main():
    errors = []
    rows = []
    for i, line in enumerate(ocr_pdf_lines(PDF_PATH)):
        rec = parse_line(line, i, errors)
        if rec:
            rows.append(rec)

    dropped = [e for e in errors if not e.startswith("LOST_YEAR_DIGIT")]
    lost_year = [e for e in errors if e.startswith("LOST_YEAR_DIGIT")]
    print(f"Parsed {len(rows)} lots, {len(dropped)} dropped lines "
          f"({len(lost_year)} kept with year=None due to an OCR digit loss).")
    no_unit = sum(1 for e in dropped if e.startswith("NO_UNIT"))
    print(f"  NO_UNIT: {no_unit}")
    for e in dropped[:15]:
        print(f"  {e}")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Wines"
    cols = ["Lot", "Wine", "Producer", "Region", "Classification",
            "Quantity", "Unit", "OHK", "Year", "Price_CHF", "Raw_Line",
            "Line_Number"]
    ws.append(cols)
    for r in rows:
        ws.append([r[c] for c in cols])
    wb.save(OUT_PATH)
    print(f"Saved {len(rows)} rows to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
