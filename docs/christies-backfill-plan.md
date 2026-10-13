# Bauplan: Christie's historischer Backfill (alle vergangenen Wein-Auktionen)

Stand: 2026-10-12 · Erstellt als Senior-Review des Ursprungsplans

---

## 1. Summary

**Ziel:** Alle historischen Christie's-Wein-Auktionen einmalig nachladen und in
die Master-DB einspielen.

**Ansatz:** Neuer, eigenständiger Backfill-Lauf (`data/run_christies_backfill.py`)
— analog zu `run_idealwine_delta.py` — statt den monatlichen Orchestrator zu
verbiegen. Sitemap-Index → department-Filter → sale_id-Auflösung (nur für
Wein-Kandidaten, wenn möglich) → lotsearch → Archiv → build_db.

**Hauptrisiken (absteigend):**

1. Falscher Wein-Filter → Bücher/Kunst in der Wein-DB (größter Schaden)
2. Identity-Key-Kollision → Duplikate zwischen Backfill und monatlichem Lauf
3. Rate-Limit/IP-Sperre → Lauf bricht bei Auktion 5000 ab, Resume verloren
4. Stille NULL-Felder → tausende Auktionen ohne Datum/Währung/Meta

**Betroffene Module:**

| Modul | Änderung |
|---|---|
| `ingest/fetchers/christies.py` | Sitemap-discover, Legacy-Meta-Parser, department-Filter |
| `data/run_christies_backfill.py` | **NEU** — eigenständiger Backfill-Runner |
| `data/orchestrate.py` | Keine (out of scope) |
| `data/build_db.py` | Keine (out of scope) |
| `ingest/registry.py` | Keine (out of scope) |
| `ingest/tests/test_christies.py` | Keine (bestehende 5 Tests müssen unverändert grün bleiben) |

---

## 2. Established Facts (live verifiziert)

1. `load_christies` (`build_db.py:729`) existiert, erwartet `event_id`
   (Fallback `sale_id`) als DB-Schlüssel. `UNIQUE(provider_id, auction_id)`,
   `INSERT OR IGNORE`.
2. Quelle der Vergangenheit: `https://www.christies.com/LotFinder_Sitemap1.xml`
   → `SiteMapPastSales1.xml` → 6 409 Auktions-URLs
   `/auction/auction-{id}-{loc}/browse-lots`.
3. Legacy-Format weicht ab:
   - **Neu** (auction-31122): `sale_id`, `sale_number`,
     `followAnalyticsMetadata.department`.
   - **Legacy** (auction-5057-par): `sale_id` (18 467), `sale_number` (5 057),
     `sale_location` (Paris), **kein** `followAnalyticsMetadata.department`.
4. lotsearch-API funktioniert mit `saleNumber` — aber **nur in Kombination** mit
   `saleid` + `saleroomcode` (sonst Cross-Auction-Treffer möglich).
5. Wein-Filter für Legacy-Seiten: **noch ungeklärt** (kein department-Feld).
6. Samsung/Google-Drive nicht gemountet; Master-DB auf Samsung.
7. `ym_date(None, None)` → `None` — datumlose Auktionen laden still und
   ohne Warnung in die DB.
8. `_auction_meta()` nutzt generische Regex (`"title":"([^"]+)"`) — auf
   Legacy-Seiten kann der erste Match Navigationstext statt Auktionstitel sein.
9. Kein Rate-Limiting, kein Retry, kein Backoff im gesamten Projekt.

**Vermutung (in Step 0 zu verifizieren):** Die Sitemap-Datei heißt
`SiteMapPastSales1.xml` — die „1" impliziert Geschwister (`…2.xml`, `…3.xml`).
Im ersten Step den Sitemap-Index parsen und alle Kinder konsumieren.

---

## 3. Scope

### In Scope

- Sitemap-Index-Parser (alle `SiteMapPastSales*.xml`)
- department-Quelle für Legacy-Seiten klären + Wein-Filter implementieren
- Legacy-Meta-Parser (getrennt von `_auction_meta` für neue Seiten)
- Backfill-Runner mit Checkpoint/Resume, Rate-Limiting, Circuit-Breaker
- Archivieren ins Christies/-Verzeichnis (kanonisches JSON)
- Einspielen via `build_db.py` (unveränderter Loader)
- Reconciliation gesamt + End-of-Run-Summary

### Out of Scope — Do-Not-Touch-Liste

Diese Dateien/Funktionen werden **nicht** verändert. Jede Abweichung
erfordert explizite Freigabe:

| Datei | Funktion/Bereich | Grund |
|---|---|---|
| `ingest/fetchers/christies.py` | `discover()` | Monatlicher Lauf unberührt |
| `ingest/fetchers/christies.py` | `_auction_meta()` neue-Format-Regex | Bestehende Semantik |
| `ingest/fetchers/christies.py` | `_all_lots()` Reconciliation-Semantik | Bestehende Guards |
| `data/build_db.py` | `load_christies()` + Schema | Format-Vertrag |
| `data/orchestrate.py` | Gesamte Datei | Monatlicher Lauf |
| `data/run_ingest.py` | PROVIDERS-Liste | Monatlicher Lauf |
| `ingest/tests/test_christies.py` | Alle 5 Tests | **Acceptance-Gate** |

### Offene Entscheidungen

**(D1) Wein-Filter-Quelle für Legacy** — Optionen:

| Option | Zuverlässigkeit | Aufwand |
|---|---|---|
| (a) sales-API mit department-Feld | Hoch (wenn existent) | Discovery nötig |
| (b) Legacy-JSON-Block auf der Auktionsseite | Hoch | Pro-Auktion ein GET |
| (c) Heuristik über Lot-Titel | **Fragil** | Gering |

**Empfehlung:** (a) oder (b) zuerst. **Harte Stop-Gate:** Wenn Step 1
keine zuverlässige Quelle findet → Halt + Report. Kein Fallback auf (c)
ohne explizite Freigabe.

**(D2) Ablage** — Backfill in CI-Artifact vs. lokal mit Samsung.

**Empfehlung:** Lokal mit Samsung. Der Backfill ist einmalig, produziert
potenziell tausende JSONs (GB-Bereich) und läuft Stunden. CI-Artifacts haben
ein Größenlimit und die Laufzeit würde die GitHub-Actions-Limits sprengen.

**(D3) Architektur** — Eigenständiger `run_christies_backfill.py` (analog
`run_idealwine_delta.py`) statt `run_provider()`.

**Begründung:** `orchestrate.run_provider()` speichert das Manifest erst am
Ende des Loops (`save_manifest` nach Zeile 76). Ein Crash bei Auktion 5 000
von 6 409 verliert alles. Der Backfill braucht Checkpoint/Resume, Rate-Limiting
und einen Circuit-Breaker — Features, die der Orchestrator nicht hat und für
den Monatslauf nicht braucht.

---

## 4. Nicht-funktionale Anforderungen (Guardrails)

### NFR-1 Vollständigkeit Sitemap

- Sitemap-**Index** parsen, nicht nur `SiteMapPastSales1.xml`.
- Assertion: jede referenzierte `SiteMapPastSales*.xml` wurde geladen.
- Jede geparste URL wird gezählt; Differenz Index-Summe vs. geparst → Abbruch.

### NFR-2 Vollständigkeit Lots (pro Auktion)

- lotsearch bis `total_hits_filtered` (bestehende Reconciliation in
  `_all_lots()` bleibt unverändert).
- Abweichung → Auktion überspringen + in Skip-Liste loggen.

### NFR-3 Korrektheit Filter

- Nur Wine & Spirits importieren.
- **Validierung:** ≥ 5 bekannte Wein-Auktionen + ≥ 5 bekannte Nicht-Wein-Auktionen,
  100 % korrekt klassifiziert. Nicht 1+1 wie im Ursprungsplan.
- Ground-Truth-Liste (sale_number → department) als Fixture pflegen.

### NFR-4 Korrektheit Meta (Legacy)

- Legacy-`sale_id`/`sale_number`/`sale_location`/`saleroomcode` aus einem
  **benannten JSON-Block** extrahieren, nicht per generischer Regex.
- Hard-Assert auf **alle** Pflichtfelder non-None:
  `sale_id` (numerisch), `sale_number` (numerisch), `saleroomcode` (2–3 Buchstaben),
  `year` (1990–2026), `month` (1–12).
- Fehlende Pflichtfelder → Auktion überspringen + Skip-Liste.

### NFR-5 Identity-Key-Konsistenz

**Kritischster Guardrail.** Monatlicher `discover()` nutzt `sale_id` als Key.
Backfill **muss denselben Key** verwenden:

- Aus der Legacy-Seite die **numerische `sale_id`** auslesen (nicht den
  URL-Token `auction-5057-par`).
- `AuctionRef.auction_id = sale_id` (String).
- Archiv-Datei: `{sale_id}.json`.
- `FetchResult.data["auction"]["event_id"] = sale_id`.
- `sale_number` und `saleroomcode` separat im Meta speichern.
- Cross-Check: `sale_id` aus HTML ≠ sale_number (sonst Parsing-Fehler).

### NFR-6 Idempotenz

- Manifest-Dedup vor jedem Fetch.
- Checkpoint-Manifest nach jeder erfolgreichen Auktion flushen (nicht am Ende).
- Wiederholungslauf: 0 neue **erfolgreiche** Fetches.
- Permanent-Skip-Liste (Auktionen ohne Lots, Parsing-Fehler) ist
  Byte-identisch über Läufe.

### NFR-7 Fail-loud + Circuit-Breaker

- Leere/fehlerhafte Auktion überspringen + in Skip-Liste (bestehender Guard).
- **Circuit-Breaker:** N konsekutive HTTP-Fehler (429/403/5xx) → Lauf abbrechen,
  nicht 6 000 Skip-Zeilen produzieren.
  Default: `MAX_CONSECUTIVE_FAILURES = 10`.
- Jeder Skip-Grund wird kategorisiert: `HTTP_ERROR`, `EMPTY_RESULT`,
  `RECONCILIATION_MISMATCH`, `META_MISSING`, `FILTER_REJECTED`.

### NFR-8 Reconciliation Gesamt

- **Vor dem Massenlauf** (nach Steps 1+2): `N_expected` (Wein-Auktionen aus
  dem Filter) berechnen und zur **manuellen Inspektion** ausgeben.
- Plausibilitäts-Warnung (Operator-Inspektion, kein hard-coded assert):
  `N_expected == N_sitemap_total` oder `N_expected < 10` → Filter vermutlich
  defekt → Operator entscheidet. Erwartbare Größenordnung: zweistellig bis
  niedriger dreistelliger Bereich, aber die tatsächliche Zahl ist unbekannt.
- **Nach dem Massenlauf:** erwartet vs. tatsächlich verarbeitet vs. übersprungen.
  Drift sichtbar in End-of-Run-Summary.

### NFR-9 Währungs-Validierung

- `_currency()` auf Legacy-Lots: Pre-2002-Auktionen (Paris, Amsterdam) können
  FRF/NLG/DEM/ATS liefern, oder Unicode-Symbole (€, £).
- Guardrail: `currency IS NOT None` für verkaufte Lots assertieren.
- Währungsverteilung im End-of-Run-Summary reporten.
- Gate: Auktion mit >50 % NULL-Währung bei verkauften Lots → Skip + Warnung.

### NFR-10 Rate-Limiting

- Konfigurierbarer Inter-Request-Delay (Default: 1.0 s).
- Exponentieller Backoff bei 429/5xx (2s → 4s → 8s → 16s → 32s → Abbruch).
- `curl_cffi` mit `impersonate="chrome"` beibehalten.

### NFR-11 Wine-Resolution-Impact

- **Vor** Backfill: `SELECT COUNT(*) FROM lots WHERE wine_ref_id IS NULL`
  und Resolution-Status-Verteilung festhalten.
- **Nach** Backfill + build_wines: dieselben Metriken.
- Delta-Report: neue Lots, neue `AMBIGUOUS`/`REVIEW_REQUIRED`, Veränderung
  der Resolution-Quote.

---

## 5. Architektur + Design

### 5.1 Komponentendiagramm

```
┌─────────────────────────────────────────────────────┐
│  data/run_christies_backfill.py  (Entry Point)      │
│  - CLI: --dry-run, --limit N, --resume, --delay     │
│  - Progress: [i/N] sale_id=… lots=…                 │
│  - End-of-Run-Summary                               │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  ingest/fetchers/christies.py  (erweitert)          │
│                                                     │
│  + discover_backfill(session)                       │
│    → Sitemap-Index → SiteMapPastSales*.xml          │
│    → alle AuctionRef(sale_id=…, sale_number=…, …)   │
│                                                     │
│  + classify_department(session, ref)                │
│    → Legacy-department-Quelle (D1-Ergebnis)         │
│    → "Wine & Spirits" | "Other"                     │
│                                                     │
│  + _legacy_auction_meta(html, ref)                  │
│    → benannter JSON-Block statt generischer Regex   │
│    → Hard-Assert auf alle Pflichtfelder             │
│                                                     │
│  fetch(session, ref)  ← UNVERÄNDERT                 │
│  _all_lots()          ← UNVERÄNDERT                 │
│  _auction_meta()      ← UNVERÄNDERT (neue Seiten)   │
│  discover()           ← UNVERÄNDERT (monatlich)     │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  Archiv: {ARCHIVE}/Christies/{sale_id}.json         │
│  (kanonisches {auction, lots} Format)               │
│  Manifest: data/ingest_manifest.json                │
│  (Checkpoint: flush nach jeder Auktion)             │
└──────────┬──────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────┐
│  data/build_db.py                                   │
│  load_christies()  ← UNVERÄNDERT                    │
│  → liest Christies/*.json, INSERT OR IGNORE         │
└─────────────────────────────────────────────────────┘
```

### 5.2 Neue Funktionen in `christies.py`

```python
def discover_backfill(session) -> list[AuctionRef]:
    """Sitemap-Index → alle SiteMapPastSales*.xml → AuctionRef-Liste.

    Jede URL wird zu sale_id aufgelöst (GET auf die Auction-Seite, nicht
    der URL-Token). Dedup über sale_id.
    """

def classify_department(session, ref) -> str:
    """Department einer Legacy-Auktion bestimmen.

    Quelle: D1-Ergebnis (sales-API oder Legacy-JSON-Block).
    Rückgabe: 'Wine & Spirits' | department-String.
    """

def _legacy_auction_meta(html, ref) -> dict:
    """Meta-Extraktion für Legacy-Seiten.

    Getrennt von _auction_meta() (neue Seiten) — andere JSON-Struktur.
    Hard-Assert: sale_id, sale_number, saleroomcode, year, month non-None.
    """
```

### 5.3 Neuer Runner `data/run_christies_backfill.py`

```
Usage: python data/run_christies_backfill.py [OPTIONS]

Options:
  --dry-run       Discovery + Filter + N_expected, kein Lot-Fetch
  --limit N       Nur die ersten N Wein-Auktionen fetchen (Smoke-Test)
  --resume        Weiter ab Checkpoint (Manifest als State)
  --delay SECS    Inter-Request-Delay (Default: 1.0)
  --max-fail N    Circuit-Breaker-Schwelle (Default: 10)
```

**Ablauf:**

1. Sitemap-Index laden → alle `SiteMapPastSales*.xml` parsen.
2. Pro URL: Auction-Seite laden → `sale_id` auslesen → `AuctionRef` bauen.
3. department-Filter (D1-Ergebnis) → Wein-Auktionen isolieren.
4. `N_expected` ausgeben. Bei `--dry-run`: Kandidatenliste schreiben + Stop.
5. Manifest-Dedup (bereits gefetchte überspringen).
6. Für jede neue Wein-Auktion:
   a. `_legacy_auction_meta()` → Meta validieren.
   b. `_all_lots()` (unverändert) → Lots fetchen + Reconciliation.
   c. JSON archivieren als `{sale_id}.json`.
   d. Manifest flushen (pro Auktion).
   e. Progress: `[42/187] sale_id=18467 sale_number=5057 lots=306`.
   f. Inter-Request-Delay.
   g. Circuit-Breaker prüfen.
7. End-of-Run-Summary schreiben.

### 5.4 lotsearch-Parameter für Legacy

```python
_lotsearch_params(meta, page)  # Bestehende Funktion

# KRITISCH: Alle drei Felder müssen non-empty sein:
# - saleid    → aus sale_id (numerisch, von der Auction-Seite)
# - salenumber → aus sale_number
# - saleroomcode → aus sale_room_code
#
# Cross-Check: ein gesampelter Lot-URL muss /auction/auction-{sale_id}
# enthalten. Sonst: falscher Sale, RuntimeError.
```

### 5.5 Operator-UX (Batch-Experience)

Da es kein UI gibt, ist die Operator-Experience der Terminal-Output:

**Progress (pro Auktion):**
```
[  1/187] sale_id=18467  sale_number=5057   lots=306   ✓ 1.2s
[  2/187] sale_id=19882  sale_number=5289   lots=  0   SKIP empty
[  3/187] sale_id=20001  sale_number=5301   lots=412   ✓ 2.1s
[  4/187] sale_id=20100  sale_number=5310   HTTP 429   RETRY 4s
[  4/187] sale_id=20100  sale_number=5310   lots=189   ✓ 5.3s
```

**End-of-Run-Summary (Format-Beispiel — Zahlen sind fiktiv):**
```
═══════════════════════════════════════════════════════
  Christie's Backfill — End of Run
═══════════════════════════════════════════════════════
  Sitemap URLs gesamt:          6 409
  Davon Wine & Spirits:           187  (N_expected)
  Bereits im Manifest:             0
  Neu zu fetchen:                 187
  ─────────────────────────────────────────────────────
  Erfolgreich:                    182
  Skip (empty):                     2
  Skip (reconciliation):           1
  Skip (meta missing):             1
  Skip (HTTP error):               1
  ─────────────────────────────────────────────────────
  Lots gesamt:                 47 231
  Davon verkauft:              38 104  (80.7 %)
  Währungsverteilung:
    GBP: 28 412   HKD: 9 100   USD: 5 819
    CHF: 2 100   FRF: 1 200   EUR: 600
  NULL-Währung (verkauft):          0
  ─────────────────────────────────────────────────────
  Skip-Liste: data/christies_backfill_skips.json
  Dauer: 3h 42min
═══════════════════════════════════════════════════════
```

**Skip-Liste** (`data/christies_backfill_skips.json`):
```json
[
  {"sale_id": "19882", "sale_number": "5289", "reason": "EMPTY_RESULT",
   "detail": "total_hits_filtered=0"},
  {"sale_id": "20555", "sale_number": "5400", "reason": "HTTP_ERROR",
   "detail": "429 Too Many Requests after 3 retries"}
]
```

---

## 6. Evolutionary Micro-Steps

### Step 0 — Sitemap-Index verifizieren (30 min)

**Aktion:** `curl` auf `LotFinder_Sitemap1.xml`, alle
`SiteMapPastSales*.xml`-Kinder identifizieren, Gesamtzahl URLs bestätigen.

**Validierung:** Anzahl Geschwister-Dateien und Gesamt-URL-Count dokumentieren.

**Gate:** Weiter nur wenn der Index vollständig parsbar ist.

### Step 1 — department-Quelle für Legacy klären (Discovery, 2–4 h)

**Aktion:**
1. Auf einer Legacy-Auktionsseite (z.B. auction-5057-par) nach
   department-Information suchen: eingebettete JSON-Blöcke, API-Calls,
   Meta-Tags.
2. Christie's interne APIs proben:
   `/api/discoverywebsite/auctioncalendar`, `/api/catalog/…`,
   sales-Endpoints.
3. Mindestens 10 Auktionen (5 Wein, 5 Nicht-Wein) manuell klassifizieren
   als Ground-Truth.

**Validierung:**
- ≥ 5 bekannte Wein-Auktionen korrekt als Wine & Spirits erkannt.
- ≥ 5 bekannte Nicht-Wein-Auktionen korrekt ausgeschlossen.
- 100 % korrekt. Kein Durchschnitt, keine Toleranz.

**Hard-Gate:** Wenn keine zuverlässige Quelle gefunden → HALT + Report.
Kein Fallback auf Title-Heuristik ohne explizite Freigabe.

### Step 2 — Sitemap-discover implementieren

**Aktion:**
1. `discover_backfill(session)` implementieren: Sitemap-Index →
   alle `SiteMapPastSales*.xml` → URL-Liste.
2. **Wichtig:** Die Reihenfolge Filter → Resolve vs. Resolve → Filter
   hängt vom D1-Ergebnis ab. Wenn D1 eine sales-API mit department liefert
   (Option a), zuerst filtern (billig), dann nur für Wein-Kandidaten die
   Auction-Seite laden und `sale_id` auflösen. Andernfalls (Option b):
   pro URL die Auction-Seite laden → `sale_id` + department auslesen.
   Die teure Variante (6 409 GETs à 1 s ≈ 1,8 h) nur wenn unvermeidbar.
3. Dedup über `sale_id`.
4. Assertion: alle Index-Kinder konsumiert, URL-Count == Summe aller XMLs.

**Validierung:**
- Fixture-Test mit synthetischem Sitemap-XML.
- Live-Test gegen eine Handvoll realer URLs (sale_id korrekt aufgelöst?).

**Bestehende Tests:** Alle 5 `test_christies.py`-Tests grün (Regressions-Gate).

### Step 3 — Wein-Filter + Legacy-Meta-Parser

**Aktion:**
1. `classify_department(session, ref)` implementieren (D1-Ergebnis).
2. `_legacy_auction_meta(html, ref)` implementieren — getrennt von
   `_auction_meta()`.
3. Hard-Assert auf Pflichtfelder (NFR-4).
4. lotsearch-Parameter-Validierung: `saleid` + `salenumber` + `saleroomcode`
   alle non-empty (NFR-5).
5. Cross-Check: gesampelter Lot-URL enthält die erwartete sale_id.

**Validierung:**
- Fixture-Tests:
  - Wein-Auktion → korrekt erkannt + Meta vollständig.
  - Nicht-Wein-Auktion → korrekt abgelehnt.
  - Legacy-Seite mit fehlendem Meta → `RuntimeError`.
  - lotsearch mit fehlendem `saleroomcode` → `RuntimeError`.
- Live-Test gegen ≥ 3 echte Legacy-Wein-Auktionen.
- Ground-Truth-Liste (Step 1) zu 100 % korrekt.

**Bestehende Tests:** Alle 5 `test_christies.py`-Tests grün.

### Step 4 — Backfill-Runner (Grundgerüst)

**Aktion:**
1. `data/run_christies_backfill.py` — CLI mit `--dry-run`, `--limit`,
   `--resume`, `--delay`, `--max-fail`.
2. Discovery → Filter → `N_expected` → Manifest-Dedup → Fetch-Loop.
3. Checkpoint: Manifest-Flush nach jeder Auktion.
4. Circuit-Breaker: `MAX_CONSECUTIVE_FAILURES`.
5. Rate-Limiting: `time.sleep(delay)` + Backoff bei 429/5xx.
6. Progress-Output: `[i/N] sale_id=… lots=… ✓ t`.

**Validierung:**
- `--dry-run` gibt `N_expected` aus, erstellt Kandidatenliste, fetcht nichts.
- `--limit 3` fetcht genau 3 Auktionen.
- `--resume` nach Abbruch setzt korrekt fort (0 Duplikate).
- Circuit-Breaker löst nach N Fehlern aus.
- Progress-Output lesbar und korrekt.

### Step 5 — Massenlauf + Sammeln

**Aktion:**
1. `--dry-run` ausführen → `N_expected` inspizieren.
   Plausibilitäts-Check: zweistellig bis niedriger dreistelliger Bereich
   erwartet — Operator-Entscheidung, kein harter Assert.
2. `--limit 10` Smoke-Run → End-to-End prüfen.
3. Voller Lauf (kein Limit).
4. End-of-Run-Summary inspizieren.
5. Skip-Liste prüfen: jeder Skip nachvollziehbar?

**Validierung:**
- Reconciliation Gesamt: `N_expected` vs. tatsächlich verarbeitet.
- Währungsverteilung plausibel (GBP/HKD/USD dominant, historische Währungen
  nur bei alten Auktionen).
- NULL-Währung bei verkauften Lots = 0.
- Idempotenz: Wiederholungslauf → 0 neue Fetches, Skip-Liste identisch.

### Step 6 — Einspielen in Master-DB

**Aktion:**
1. Samsung mounten.
2. `python data/build_db.py --dry-run` → Lot-Zahlen prüfen.
3. Voller Build.
4. Wine-Resolution-Impact messen (NFR-11):
   - Vorher: `wine_ref_id IS NULL`-Count, Resolution-Status-Verteilung.
   - Nachher: dieselben Metriken.
   - Delta-Report.

**Validierung:**
- `PRAGMA integrity_check` + `PRAGMA foreign_key_check` (bestehende Gates).
- Lot-Count plausibel (≈ 40 000–100 000 neue Lots).
- Keine Duplikat-Auktionen zwischen Backfill und bestehendem Bestand.
- Resolution-Quote nicht dramatisch verschlechtert.

### Step 7 — Senior-Review + Fixes

Finaler Review gegen diese Checkliste.

---

## 7. Validation Matrix

| Prüfgegenstand | Validierung | NFR |
|---|---|---|
| Sitemap-Index-Vollständigkeit | Alle Kinder konsumiert, URL-Count stimmt | NFR-1 |
| department-Filter | ≥ 10 Ground-Truth (5 Wein, 5 Nicht-Wein), 100 % | NFR-3 |
| Identity-Key | `sale_id` konsistent zwischen Backfill + Monat | NFR-5 |
| Legacy-Meta | Pflichtfelder non-None, year 1990–2026, month 1–12 | NFR-4 |
| lotsearch-Parameter | saleid + salenumber + saleroomcode non-empty | NFR-5 |
| Lot-Reconciliation | `total_hits_filtered` == `len(lots)` | NFR-2 |
| Idempotenz | Wiederholungslauf → 0 neu, Skip-Liste identisch | NFR-6 |
| Circuit-Breaker | 10 konsekutive Fehler → Abbruch | NFR-7 |
| Rate-Limiting | Backoff bei 429/5xx | NFR-10 |
| Reconciliation Gesamt | N_expected vs. tatsächlich, Drift sichtbar | NFR-8 |
| Währung | Non-None für verkaufte Lots, Verteilung geloggt | NFR-9 |
| DB-Integrität | `PRAGMA integrity_check`, `foreign_key_check` | bestehend |
| Wine-Resolution-Impact | Vorher/Nachher-Delta | NFR-11 |
| Bestehende Tests | 5 Tests in `test_christies.py` unverändert grün | Scope |
| Pylint | `.github/linters/.python-lint` Config | bestehend |

---

## 8. Risks and Rollback

| Risiko | Mitigation | Rollback |
|---|---|---|
| Falscher Wein-Filter | NFR-3 (≥ 10 Ground-Truth), Hard-Gate Step 1 | JSONs aus `Christies/` löschen, build_db neu |
| Identity-Key-Kollision | NFR-5 (sale_id als einziger Key), Cross-Check | JSONs mit falschem Key löschen, Manifest bereinigen |
| Rate-Limit/IP-Sperre | NFR-10 (Delay + Backoff), NFR-7 (Circuit-Breaker) | `--resume` ab Checkpoint |
| Stille NULL-Felder | NFR-4 (Hard-Assert), NFR-9 (Währungs-Validierung) | Betroffene JSONs neu fetchen oder aus DB-Build ausschließen |
| Teil-Import (Pagination) | NFR-2 (bestehende Reconciliation) | Betroffene Auktion re-fetchen |
| Masse (6 409 URLs) | `--dry-run` + N_expected-Gate (NFR-8) | Additiv — Backfill-JSONs entfernen + rebuild |
| Resolution-Degradation | NFR-11 (Vorher/Nachher-Metriken) | JSONs entfernen, rebuild, build_wines neu |

**Genereller Rollback:** `build_db.py` baut die DB jedes Mal komplett neu.
Rollback = Backfill-JSONs aus `Christies/` entfernen + `build_db.py` ausführen.
Manifest-Einträge der Backfill-Auktionen entfernen. Kein SQL-DELETE nötig.

---

## 9. Projekt-Konventionen (für den Implementierer)

| Konvention | Beispiel |
|---|---|
| Logging | `print(..., flush=True)` für Progress, `print(..., file=sys.stderr)` für Fehler. **Kein `logging`-Modul.** |
| Sprache | Meldungen Deutsch/Englisch gemischt (bestehend), neue Meldungen auf Englisch. |
| Linting | Pylint mit `.github/linters/.python-lint` (relaxed: kein missing-docstring etc.) |
| Tests | `unittest`, Fixtures als Modul-Konstanten, `FakeSession`/`FakeResponse`-Pattern |
| Datenmodelle | `AuctionRef`, `FetchResult` aus `ingest/models.py` — verwenden, nicht neu erfinden |
| Archiv-Format | `{ARCHIVE}/Christies/{sale_id}.json` — kanonisches `{auction, lots}` JSON |
| HTTP-Client | `curl_cffi.requests.Session(impersonate="chrome")` |
| Manifest | `ingest/registry.py` — `load_manifest`, `save_manifest`, `dedup`, `mark_fetched` |

---

## 10. Acceptance Criteria (Zusammenfassung)

1. `python -m unittest ingest.tests.test_christies` — alle 5 bestehenden Tests grün, **unverändert**.
2. `python data/run_christies_backfill.py --dry-run` — gibt `N_expected` aus, Kandidatenliste, kein Fetch.
3. `python data/run_christies_backfill.py --limit 5` — 5 Auktionen End-to-End, korrekte JSONs im Archiv.
4. Wiederholungslauf von (3) — 0 neue Fetches.
5. `python data/build_db.py` gegen das Archiv — `PRAGMA integrity_check` OK.
6. Neue Fixture-Tests für: Sitemap-Parser, department-Filter, Legacy-Meta-Parser.
7. End-of-Run-Summary enthält alle Felder aus Abschnitt 5.5.
8. Skip-Liste als JSON-Datei, jeder Skip kategorisiert und nachvollziehbar.
9. Pylint ohne neue Warnungen (bestehende Baseline).

---

## 11. Approval Gate

Freigabe für:
- Gesamtscope wie oben beschrieben
- D1: Wein-Filter-Quelle → Step 1 entscheidet, Hard-Gate bei Misserfolg
- D2: Lokal mit Samsung (empfohlen)
- D3: Eigenständiger `run_christies_backfill.py`

Danach: PLANNING → IMPLEMENTING.
