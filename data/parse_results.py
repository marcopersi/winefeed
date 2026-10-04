"""Parse downloaded result files (XLSX/PDF) into the auction+lot JSON shape.

Consolidates the "PDF-parsing way" (Weg B) in Python:

- ``parse_weinauktionator_xlsx`` reads the Weinauktionator result XLSX.
- ``parse_hdh_pdf`` extracts the Hart Davis Hart result table from a PDF.
"""
import re

import pdfplumber


# --- Weinauktionator (XLSX) ------------------------------------------------- #

def parse_weinauktionator_xlsx(path):
    import openpyxl

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))

    title = _clean(rows[0][0]) if rows else None
    date = _parse_date(_clean(rows[1][0]) if len(rows) > 1 else None)

    header_idx = None
    for i, row in enumerate(rows):
        if row and row[0] == "Lot":
            header_idx = i
            break

    lots = []
    if header_idx is not None:
        for row in rows[header_idx + 1:]:
            if not row or row[0] is None:
                continue
            hammer = row[3] if len(row) > 3 else None
            lots.append({
                "lot_no": str(row[0]),
                "region": _clean(row[1]),
                "wine": _clean(row[2]),
                "hammer_price": hammer if isinstance(hammer, (int, float)) else None,
                "format": _clean(row[4]) if len(row) > 4 else None,
            })

    return {
        "auction": {
            "id": None,
            "name": title,
            "date": date,
            "source": "weinauktionator",
        },
        "lots": lots,
    }


# --- Hart Davis Hart (PDF) -------------------------------------------------- #

_LOT_LINE = re.compile(
    r"^(\d+)\s+(\d+)\s+(.+?)\s+([\d,]{3,})\s*-\s*([\d,]{3,})\s+"
    r"([\d,]{3,})\s+([\d,]+\.\d{2})$")


def parse_hdh_pdf(path):
    with pdfplumber.open(path) as pdf:
        text = "\n".join((page.extract_text() or "") for page in pdf.pages)

    lines = text.splitlines()
    title = _hdh_title(lines)
    sale_number = _hdh_sale_number(lines)

    lots = []
    for line in lines:
        match = _LOT_LINE.match(line.strip())
        if not match:
            continue
        lots.append({
            "lot_no": int(match.group(1)),
            "qty": int(match.group(2)),
            "description": match.group(3).strip(),
            "estimate": f"{match.group(4)} - {match.group(5)}",
            "hammer": _us_number(match.group(6)),
            "aggregate": _us_number(match.group(7)),
        })

    year, month = _sale_year_month(sale_number)
    return {
        "auction": {
            "sale_number": sale_number,
            "name": title,
            "year": year,
            "month": month,
            "source": "hdh",
        },
        "lots": lots,
    }


def _hdh_title(lines):
    for line in lines[:6]:
        line = line.strip()
        if line and "Auction" in line and "Results" not in line:
            return line
    return None


def _hdh_sale_number(lines):
    for line in lines[:6]:
        match = re.search(r"^(\d{4})\s+Auction\s+Results", line.strip())
        if match:
            return match.group(1)
    return None


def _sale_year_month(sale_number):
    if sale_number and len(sale_number) == 4:
        return 2000 + int(sale_number[:2]), int(sale_number[2:])
    return None, None


def _us_number(text):
    return float(text.replace(",", "")) if text else None


def _clean(value):
    return str(value).strip() if value not in (None, "") else None


def _parse_date(value):
    if not value:
        return None
    match = re.search(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", value)
    if match:
        return f"{match.group(3)}-{match.group(2)}-{match.group(1)}"
    return value
