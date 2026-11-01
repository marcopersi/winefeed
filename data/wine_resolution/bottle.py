"""Bottle-format and quantity parsing from wine-name bracket hints.

Auction titles often carry the lot size as ``(6 BT)`` or ``(3 MAG)``. This is
the only source of quantity + bottle size for several houses, so it must be
parsed exactly. ``quantity`` is the bottle count, ``bottle_size_dl`` the size in
deciliters.
"""
import re

# Format abbreviations -> deciliters. Only real bottle formats; label-state
# codes (E.T.H, E.L.A, ...) are intentionally absent so they are never parsed.
BOTTLE_FORMATS = {
    "BT": 7.5, "BTS": 7.5, "BOTTLE": 7.5, "BOTTLES": 7.5,
    "BOUTEILLE": 7.5, "BOUTEILLES": 7.5, "FL": 7.5,
    "FLASCHE": 7.5, "FLASCHEN": 7.5,
    "HB": 3.75, "HFBT": 3.75, "HFLT": 3.75, "HALF": 3.75,
    "MAG": 15.0, "MAGN": 15.0, "MAGNUM": 15.0, "MAGNUMS": 15.0, "MG": 15.0,
    "DM": 30.0, "DOUBLEMAGNUM": 30.0,
    "IMP": 60.0, "IMPERIALE": 60.0, "METH": 60.0, "METHUSELAH": 60.0,
    "REHOBOAM": 45.0,
    "SALR": 90.0, "SALMANAZAR": 90.0,
    "BALR": 120.0, "BALTHAZAR": 120.0,
    "NEBR": 150.0, "NEBUCHADNEZZAR": 150.0,
    "MELR": 180.0, "MELCHIOR": 180.0,
}

_LITER_FORMATS = {"L", "LTR", "LITR", "LITER"}

_BRACKET = re.compile(r"\(\s*(\d+)\s*([A-Za-z.]+)\s*\)")
_PLAIN = re.compile(r"\b(\d+)\s*([A-Za-z.]+)\b")
_LITER = re.compile(r"(\d+(?:[.,]\d+)?)\s*l(?:iter|tr)?\b", re.IGNORECASE)


def parse_bottle_format(name, description=None):
    """Parse a ``(6 BT)``, ``12 Bouteilles`` or ``0,75l`` hint into (qty, dl).

    Searches both the name and the description (some houses put the lot size
    only in the description). Returns ``(None, None)`` when there is no
    recognised hint, so unknown/ambiguous codes are never guessed.
    """
    for text in (name, description):
        if not text:
            continue
        for m in _BRACKET.finditer(str(text)):
            number = int(m.group(1))
            fmt = m.group(2).upper().replace(".", "")
            if fmt in BOTTLE_FORMATS:
                return number, BOTTLE_FORMATS[fmt]
            if fmt in _LITER_FORMATS:
                return 1, number * 10
        for m in _PLAIN.finditer(str(text)):
            number = int(m.group(1))
            fmt = m.group(2).upper().replace(".", "")
            if fmt in BOTTLE_FORMATS:
                return number, BOTTLE_FORMATS[fmt]
        for m in _LITER.finditer(str(text)):
            liters = float(m.group(1).replace(",", "."))
            return 1, liters * 10
    return None, None


def strip_bottle_format(name):
    """Remove a recognised bottle-format mention (``(6 BT)``, ``2 Magnums``,
    ``0,75l``) from ``name``.

    The bottle format is an attribute (``quantity``/``bottle_size_dl``), not
    part of the wine's identity (leitmotiv Sec. 0: "name = reiner Wein-Name
    ... ohne Gebinde"), so it must not survive into ``canonical_name`` /
    ``alias_key`` -- left in, "Sassicaia" and "Sassicaia (2 BT)" fragment
    into two different wines rows for the same real wine. Only removes a
    match ``parse_bottle_format`` itself would recognise (same precedence:
    bracket, then plain, then liter), so an unrecognised number is never
    guessed away; a bare format word with no leading count (e.g. a lone
    "Magnum") is intentionally not covered -- that is a quantity, not a
    display, question, outside the scope of this cleanup."""
    if not name:
        return name
    for m in _BRACKET.finditer(name):
        fmt = m.group(2).upper().replace(".", "")
        if fmt in BOTTLE_FORMATS or fmt in _LITER_FORMATS:
            return re.sub(r"\s+", " ", name[:m.start()] + name[m.end():]).strip()
    for m in _PLAIN.finditer(name):
        fmt = m.group(2).upper().replace(".", "")
        if fmt in BOTTLE_FORMATS:
            return re.sub(r"\s+", " ", name[:m.start()] + name[m.end():]).strip()
    for m in _LITER.finditer(name):
        return re.sub(r"\s+", " ", name[:m.start()] + name[m.end():]).strip()
    return name
