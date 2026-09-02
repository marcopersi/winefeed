"""Vintage separation.

A vintage is an attribute of a wine, not part of its identity. This module
extracts a vintage from a raw wine name and separates it from the wine key.

The raw name is never mutated. The result is a status plus a cleaned name that
has the *accepted* vintage token removed.
"""
import re

_YEAR = r"(?:1[7-9]\d{2}|20\d{2})"
# A vintage only counts when it appears in one of these positions.
_LEADING = re.compile(rf"^\s*({_YEAR})\b")
_TRAILING = re.compile(rf"\b({_YEAR})\s*(?:\([^)]*\))?\s*$")
_VINTAGE_WORD = re.compile(rf"\bVintage\s+({_YEAR})\b", re.IGNORECASE)

# Words that make a neighbouring year part of the product name, not a vintage.
_NEG_AFTER_YEAR = {"disgorgement", "established", "founded", "bottled", "made"}
_NEG_BEFORE_YEAR = {"cuvee", "cuvée", "bin", "ad", "lot", "n", "no", "numéro"}

_NV = re.compile(r"\b(nv|n\.v\.|non[\s-]vintage|sans[\s-]ann[ée]e)\b", re.IGNORECASE)
_MV = re.compile(r"\b(mv|multi[\s-]vintage|vertical|assortment)\b", re.IGNORECASE)

_YEAR_ANY = re.compile(rf"\b({_YEAR})\b")

STATUS_STRUCTURED = "STRUCTURED"
STATUS_EXTRACTED = "EXTRACTED"
STATUS_NV = "NV"
STATUS_MV = "MV"
STATUS_MISSING = "MISSING"
STATUS_AMBIGUOUS = "AMBIGUOUS"
STATUS_CONFLICT = "CONFLICT"
STATUS_INVALID = "INVALID"


def _valid_structured(vintage, auction_year):
    if vintage is None:
        return False
    if not 1700 <= vintage <= 2100:
        return False
    if auction_year is not None and vintage > auction_year:
        return False
    return True


def resolve_vintage(raw_name, structured_vintage=None, auction_year=None):
    """Resolve the vintage for one wine observation.

    Returns a dict with keys:
      status, final, extracted, rule_id, evidence, cleaned_name
    """
    name = raw_name if isinstance(raw_name, str) else ""

    # All years present in the name (for ambiguity detection).
    years = [int(y) for y in _YEAR_ANY.findall(name)]
    distinct_years = set(years)

    # NV is recognised before any year regex.
    if _NV.search(name):
        return {
            "status": STATUS_NV, "final": None, "extracted": None,
            "rule_id": "nv-keyword", "evidence": name, "cleaned_name": name,
        }

    # Multiple distinct years are inherently ambiguous (e.g. verticals).
    if len(distinct_years) > 1:
        return {
            "status": STATUS_AMBIGUOUS, "final": None, "extracted": None,
            "rule_id": "multiple-years", "evidence": name,
            "cleaned_name": name,
        }

    # MV without an explicit year list.
    if _MV.search(name):
        return {
            "status": STATUS_MV, "final": None, "extracted": None,
            "rule_id": "mv-keyword", "evidence": name, "cleaned_name": name,
        }

    # Extract from an accepted position only.
    extracted = None
    rule_id = None
    evidence = None
    m = _LEADING.search(name)
    if m:
        extracted = int(m.group(1))
        rule_id = "leading-year"
        evidence = name
    else:
        m = _TRAILING.search(name)
        if m:
            extracted = int(m.group(1))
            rule_id = "trailing-year"
            evidence = name
        else:
            m = _VINTAGE_WORD.search(name)
            if m:
                extracted = int(m.group(1))
                rule_id = "vintage-keyword"
                evidence = name

    # Reject a year that is part of the product name (negative context).
    if extracted is not None and _is_negative_context(name):
        return {
            "status": STATUS_MISSING, "final": None, "extracted": None,
            "rule_id": "negative-context", "evidence": name,
            "cleaned_name": name,
        }

    # Structured vintage handling.
    if structured_vintage is not None:
        if not _valid_structured(structured_vintage, auction_year):
            return {
                "status": STATUS_INVALID, "final": None, "extracted": None,
                "rule_id": "structured-invalid",
                "evidence": str(structured_vintage), "cleaned_name": name,
            }
        if extracted is not None and extracted != structured_vintage:
            return {
                "status": STATUS_CONFLICT, "final": None, "extracted": None,
                "rule_id": "structured-vs-extracted-conflict",
                "evidence": f"structured={structured_vintage} extracted={extracted}",
                "cleaned_name": name,
            }
        # Structured wins; the year is already a separate attribute.
        return {
            "status": STATUS_STRUCTURED, "final": structured_vintage,
            "extracted": None, "rule_id": "structured",
            "evidence": str(structured_vintage), "cleaned_name": name,
        }

    # No structured vintage: rely on extraction only.
    if extracted is None:
        return {
            "status": STATUS_MISSING, "final": None, "extracted": None,
            "rule_id": "no-year", "evidence": name, "cleaned_name": name,
        }

    if auction_year is not None and extracted > auction_year:
        return {
            "status": STATUS_INVALID, "final": None, "extracted": None,
            "rule_id": "year-after-auction",
            "evidence": f"extracted={extracted} auction={auction_year}",
            "cleaned_name": name,
        }

    cleaned = _remove_token(name, extracted)
    return {
        "status": STATUS_EXTRACTED, "final": extracted,
        "extracted": extracted, "rule_id": rule_id, "evidence": evidence,
        "cleaned_name": cleaned,
    }


def _is_negative_context(name):
    m = _YEAR_ANY.search(name)
    if not m:
        return False
    before = name[:m.start()].strip().lower()
    after = name[m.end():].strip().lower()
    if before.split() and before.split()[-1].rstrip(".,;:") in _NEG_BEFORE_YEAR:
        return True
    if after.split() and after.split()[0].rstrip(".,;:") in _NEG_AFTER_YEAR:
        return True
    return False


_QTY_BRACKET = re.compile(
    r"\s*\(\s*\d+\s*(?:BT|MAG|DM|HB|IMP|LTR?|JM\d*)\s*\)\s*$",
    re.IGNORECASE)


def _remove_token(name, year):
    """Remove the accepted vintage token and a trailing quantity bracket."""
    token = str(year)
    name = re.sub(rf"\b{token}\b", " ", name)
    name = _QTY_BRACKET.sub(" ", name)
    return re.sub(r"\s+", " ", name).strip()
