"""Producer + wine matching against the reference lists (§4.2/4.3).

§4.2: inverted token index over ``producers.csv`` with set intersection.
§4.3: producer-scoped fuzzy match (``rapidfuzz.token_set_ratio``) over
``wines_by_producer.csv``.
"""
import csv
import os
from fractions import Fraction

from rapidfuzz import fuzz

from .normalize import normalize

_REFERENCE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "..", "reference")
PRODUCERS_PATH = os.path.join(_REFERENCE, "producers.csv")
WINES_PATH = os.path.join(_REFERENCE, "wines_by_producer.csv")

# A producer is a match when it covers at least this fraction of its tokens.
PRODUCER_COVERAGE = 0.5
# A wine is a match when the fuzzy ratio is at least this.
WINE_THRESHOLD = 80.0

# Generic words that appear across many producer aliases and must not drive
# a match on their own: producer-type words, connectors common in "full
# name" aliases, and classification terms ("Grand Cru", "GCC" = Grand Cru
# Classé, "1er"/Premier Cru) that show up in appellation-only text with no
# producer at all. Validated against both the full producers.csv
# self-consistency sweep (1008 aliases, see wine-pipeline-v2.md §4.2 note)
# and data/tests/fixtures/gold_lots.csv (reduced false positives 6/406 ->
# 2/406 with no new ones) — this list is load-bearing, not cosmetic.
STOPWORDS = {"wein", "weingut", "weinguter", "domaine", "chateau", "tenuta",
             "maison", "dom", "ch",
             "de", "du", "des", "la", "le", "les", "et", "d", "l",
             "grand", "vin", "clos", "vieux", "cru", "gcc", "premier", "1er"}


def _load_producers():
    alias_to_canonical = {}
    with open(PRODUCERS_PATH, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            canonical = r["canonical"].strip()
            alias_to_canonical[normalize(canonical)] = canonical
            alias = (r.get("alias") or "").strip()
            if alias:
                alias_to_canonical[normalize(alias)] = canonical
    return alias_to_canonical


def _load_wines():
    producer_wines = {}
    with open(WINES_PATH, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            producer = r["producer"].strip()
            wine = r["wine"].strip()
            producer_wines.setdefault(producer, {})[normalize(wine)] = wine
            alias = (r.get("alias") or "").strip()
            if alias:
                producer_wines[producer][normalize(alias)] = wine
    return producer_wines


class ProducerMatcher:
    """Match raw text against the producer + wine reference lists."""

    def __init__(self):
        self.alias_to_canonical = _load_producers()
        self.producer_wines = _load_wines()
        # Tokens per *alias* (not per canonical producer): coverage must be
        # measured against whichever specific name actually matched, not
        # against the canonical name's own (possibly unrelated-length)
        # token count — see match_producer.
        self.alias_tokens = {
            alias_key: frozenset(t for t in alias_key.split()
                                  if t not in STOPWORDS)
            for alias_key in self.alias_to_canonical
        }
        self.index = {}
        for alias_key, tokens in self.alias_tokens.items():
            for token in tokens:
                self.index.setdefault(token, set()).add(alias_key)

    def match_producer(self, text):
        """Return the canonical producer if the text matches one, else None."""
        tokens = frozenset(t for t in normalize(text).split()
                            if t not in STOPWORDS)
        if not tokens:
            return None
        candidate_aliases = set()
        for token in tokens:
            candidate_aliases.update(self.index.get(token, ()))
        if not candidate_aliases:
            return None
        # For each candidate producer, take its *best-matching alias*
        # (coverage = overlap / that alias's own token count — never the
        # canonical name's token count, which may belong to a differently-
        # sized name than the alias that actually matched). This is what
        # keeps e.g. input "Moët Chandon" from being out-covered by "Dom
        # Pérignon" through its long alias "Moët & Chandon Dom Pérignon":
        # that alias's own coverage (2/3) loses to "Moët & Chandon"'s own
        # alias (2/2).
        best_per_canonical = {}
        for alias_key in candidate_aliases:
            alias_tok = self.alias_tokens[alias_key]
            if not alias_tok:
                continue
            overlap = len(tokens & alias_tok)
            score = (Fraction(overlap, len(alias_tok)), overlap)
            canonical = self.alias_to_canonical[alias_key]
            if score > best_per_canonical.get(canonical, (Fraction(0), 0)):
                best_per_canonical[canonical] = score
        if not best_per_canonical:
            return None
        # A genuine tie between two *different* producers is not an
        # "eindeutiger Treffer" (§4.2) — report no match rather than guess
        # via dict/set iteration order (hash-order, not deterministic
        # intent).
        scored = sorted(((score, canonical) for canonical, score
                         in best_per_canonical.items()), reverse=True)
        best_score, best = scored[0]
        if len(scored) > 1 and scored[1][0] == best_score:
            return None
        if best_score[0] >= PRODUCER_COVERAGE:
            return best
        return None

    def canonical_producer(self, text):
        """Canonicalize an already-known producer name/variant.

        Unlike :meth:`match_producer` (which extracts a producer from a
        *wine* name that may contain extra words), this assumes ``text`` is
        itself a producer name and should resolve exact aliases first,
        falling back to the token-coverage match for near-variants that
        aren't in ``producers.csv`` verbatim.
        """
        exact = self.alias_to_canonical.get(normalize(text))
        if exact:
            return exact
        return self.match_producer(text)

    def match_wine(self, producer, text):
        """Return the canonical wine for a producer, else None."""
        wines = self.producer_wines.get(producer)
        if not wines:
            return None
        key = normalize(text)
        best = None
        best_score = 0.0
        for wine_key, canonical in wines.items():
            score = fuzz.token_set_ratio(key, wine_key)
            if score > best_score:
                best_score = score
                best = canonical
        if best_score >= WINE_THRESHOLD:
            return best
        return None
