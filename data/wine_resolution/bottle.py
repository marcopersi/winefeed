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

# A number followed by a hyphenated/spaced compound ("Double-Magnum",
# "Double Magnum") never reached BOTTLE_FORMATS: the single-token key
# ("DOUBLEMAGNUM") only matched the first word ("DOUBLE"), which isn't a
# format on its own -- confirmed real case, besch-cannes' own
# descriptions ("1 Double-Magnum CHÂTEAU LARMANDE"). Collapse the
# separator before the bracket/plain lookup so the single-token key
# still matches.
_COMPOUND = re.compile(r"double[\s-]+magnum", re.IGNORECASE)
# Same compound, but anchored to an explicit leading count -- used by
# strip_bottle_format, which must remove the exact matched span from the
# UNTOUCHED original string (unlike parse_bottle_format's _COMPOUND.sub,
# which only normalizes a throwaway copy used for matching, not for
# position-accurate removal).
_COMPOUND_WITH_COUNT = re.compile(r"\b\d+\s*double[\s-]+magnum\b",
                                   re.IGNORECASE)

# A handful of oversized formats are unambiguous even as a BARE mention
# with no leading count at all -- a wine name ending in "... Magnum" (no
# digit in front) still means "this bottle is a Magnum" regardless of
# how many the lot contains (quantity is a separate question, see the
# ``qty=None`` return below). Confirmed real case: dorotheum never puts
# a count in front ("... 95 Parker-Punkte, Magnum"), so _PLAIN (which
# requires a leading digit) never fired for any of its lots, and they
# all fell through to the generic 7,5 dl default -- silently halving
# every such lot's price_per_bottle_eur (hammer price of a Magnum
# divided by 7,5 dl instead of 15 dl).
#
# This is an allow-list of KEYS into BOTTLE_FORMATS, not a second table
# of values, specifically to avoid two sources of truth for the same dl
# number drifting apart. Deliberately narrow -- checked each candidate
# word against the live archive for a real collision before including
# it (``grep``/`parse_bottle_format` against real `wine`/`description`
# text), and several obvious candidates turned out NOT to be safe bare
# words, so they stay excluded (still require an explicit leading
# count/bracket, same as before this fix):
#   IMPERIAL/IMPERIALE -- CVNE's Rioja "Imperial" (confirmed, winefields)
#   JEROBOAM/REHOBOAM   -- no single dl value across regions (3 l
#                          Champagne vs. 5 l Bordeaux for Jeroboam)
#   BALTHAZAR           -- Franck Balthazar, a real Cornas producer
#                          (confirmed, 158 live matches)
#   MELCHIOR            -- "Don Melchior", Concha y Toro's flagship
#                          Chilean wine (confirmed, live matches)
#   DEMI / HALF         -- "Demi-Sec" (a Champagne/Vouvray sweetness
#                          level, confirmed 395 live matches) and "half"
#                          turning up in unrelated text ("half dozen",
#                          "half sweet", even "half day corporate
#                          training") far more often than as a size word
#   DM                  -- a real producer's product-line code
#                          ("DENTON HILL VINEYARDS DM Chardonnay",
#                          confirmed live) -- plausibly also a pre-2002
#                          Deutsche-Mark price reference in the archive
_BARE_KEYS = {
    "MAGNUM", "MAGNUMS", "MAG", "MAGN",
    "DOUBLEMAGNUM",
    "METHUSELAH", "METH",
    "SALMANAZAR", "SALR",
    "NEBUCHADNEZZAR", "NEBR",
    "MELR", "BALR",  # the abbreviations alone, unlike the full words above
}
_BARE_FORMATS = {k: v for k, v in BOTTLE_FORMATS.items() if k in _BARE_KEYS}
_BARE_FORMATS["HALBFLASCHE"] = 3.75  # not in BOTTLE_FORMATS; checked safe
_BARE = re.compile(r"\b(" + "|".join(_BARE_FORMATS) + r")\b", re.IGNORECASE)


def parse_bottle_format(name, description=None):
    """Parse a ``(6 BT)``, ``12 Bouteilles`` or ``0,75l`` hint into (qty, dl).

    Searches both the name and the description (some houses put the lot size
    only in the description). Returns ``(None, None)`` when there is no
    recognised hint, so unknown/ambiguous codes are never guessed.

    Explicit hints (bracket/plain/liter, each carrying their own count) are
    checked across BOTH texts before the low-precision bare-word fallback is
    tried on either -- a bare match in ``name`` (e.g. a false-positive-free
    but still just-a-size-word match) must never pre-empt a stronger,
    explicit-count hint sitting in ``description``, or vice versa.
    """
    texts = [_COMPOUND.sub("DoubleMagnum", str(t)) for t in (name, description)
             if t]
    for text in texts:
        for m in _BRACKET.finditer(text):
            number = int(m.group(1))
            fmt = m.group(2).upper().replace(".", "")
            if fmt in BOTTLE_FORMATS:
                return number, BOTTLE_FORMATS[fmt]
            if fmt in _LITER_FORMATS:
                return 1, number * 10
        for m in _PLAIN.finditer(text):
            number = int(m.group(1))
            fmt = m.group(2).upper().replace(".", "")
            if fmt in BOTTLE_FORMATS:
                return number, BOTTLE_FORMATS[fmt]
        for m in _LITER.finditer(text):
            liters = float(m.group(1).replace(",", "."))
            return 1, liters * 10
    for text in texts:
        bm = _BARE.search(text)
        if bm:
            # No leading count was found anywhere above, so there is no
            # real quantity hint here -- qty=None (not 1), so the caller
            # (build_wines._parse_bottle_formats) never mistakes "no
            # count found" for "confirmed single bottle" and fabricates
            # quantity=1 via its own COALESCE(quantity, qty) update.
            return None, _BARE_FORMATS[bm.group(1).upper()]
    return None, None


def strip_bottle_format(name):
    """Remove a recognised bottle-format mention (``(6 BT)``, ``2 Magnums``,
    ``0,75l``) from ``name``.

    The bottle format is an attribute (``quantity``/``bottle_size_dl``), not
    part of the wine's identity (leitmotiv Sec. 0: "name = reiner Wein-Name
    ... ohne Gebinde"), so it must not survive into ``canonical_name`` /
    ``alias_key`` -- left in, "Sassicaia" and "Sassicaia (2 BT)" fragment
    into two different wines rows for the same real wine. Only removes a
    match with an explicit leading count (same precedence as
    ``parse_bottle_format``: bracket, then plain, then liter), so an
    unrecognised number is never guessed away. Deliberately does NOT also
    strip ``parse_bottle_format``'s bare-word fallback (a lone trailing
    "Magnum", no digit) -- that fallback only feeds ``bottle_size_dl``;
    keeping the word in the display name is a separate, lower-stakes
    question (does "Sassicaia" vs. "Sassicaia Magnum" need to collapse
    into one wine row?) left untouched here, out of scope for this fix."""
    if not name:
        return name
    # Gate-G0 review fix: a hyphenated/spaced "Double-Magnum"/"Double
    # Magnum" mention is correctly SIZED by parse_bottle_format (via its
    # _COMPOUND.sub normalization), but that normalization only touches a
    # local copy used for matching -- it was never mirrored here, so the
    # un-stripped compound text survived into canonical_name/alias_key,
    # fragmenting e.g. "1 Double-Magnum CHÂTEAU LARMANDE" and "CHÂTEAU
    # LARMANDE" into two different wine_ref_id rows for the same real
    # wine (confirmed live: hundreds of lots contain this pattern) --
    # exactly what this function exists to prevent. Matched directly
    # against the real text (not a normalized copy) so the removed span
    # always lines up with the original string.
    for m in _COMPOUND_WITH_COUNT.finditer(name):
        return re.sub(r"\s+", " ", name[:m.start()] + name[m.end():]).strip()
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
