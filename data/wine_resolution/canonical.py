"""Canonical-name selection.

The canonical name is a display name with correct original spelling
(e.g. ``Château Margaux``, ``Pétrus``), never the accent-stripped matching key.
"""
_DIACRITICS = set("éèêëàâçôûîïüöäÉÈÊËÀÂÇÔÛÎÏÜÖÄ")


def _has_diacritics(value):
    return any(c in _DIACRITICS for c in value)


def choose_canonical(candidates, idealwine_name=None):
    """Pick the canonical name from ``[(raw, count), ...]`` candidates.

    Priority: curated/idealwine reference, then diacritics, then not-all-caps,
    then evidence count, then alphabetical for determinism.
    """
    if idealwine_name:
        return idealwine_name
    if not candidates:
        return ""
    ranked = sorted(candidates, key=lambda c: (
        -int(_has_diacritics(c[0])),
        -int(not c[0].isupper()),
        -c[1],
        c[0],
    ))
    return ranked[0][0]
