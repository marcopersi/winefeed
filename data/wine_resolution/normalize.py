"""Text normalization for wine-name matching.

The normalized form is a *technical matching key*, not a display name. It
removes diacritics, case, apostrophes, punctuation and whitespace differences
so that ``Chateau Margaux`` and ``Château Margaux`` produce the same key.

Rules are deterministic and versioned via ``NORMALIZER_VERSION``.
"""
import re
import unicodedata

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")


def normalize(value):
    """Return a normalized matching key for a raw name.

    ``None`` and blank values yield ``""`` (never a key for a real wine).
    """
    if value is None:
        return ""
    s = str(value)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = s.replace("--", " ").replace("_", " ")
    s = s.replace("'", " ").replace("\u2019", " ")
    s = _PUNCT.sub(" ", s)
    s = _WS.sub(" ", s).strip()
    return s


def is_valid_name(value):
    """True if the value is a plausible wine name (not noise/empty).

    Rejects obviously corrupted values such as ``""``, ``"1"``, ``"2"`` or
    ``"1 ^,,^^,,^"``. A normalized key is valid if it has at least one letter.
    """
    key = normalize(value)
    if not key:
        return False
    return bool(re.search(r"[a-z]", key))
