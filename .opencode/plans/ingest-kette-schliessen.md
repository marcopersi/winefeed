# Bauplan: Ingest-Kette vollständig schließen (Fetcher ↔ Loader ↔ Scheduler)

## 1. Summary

- **Gewünscht:** Alle fetchbaren Häuser werden systematisch inkrementell
  nachgeladen (discover → Manifest-Dedup → fetch → archivieren) und von
  `build_db.py` normalisiert in die DB geladen. Vollständig, verlässlich,
  verbindlich, gehärtet, getestet.
- **Betroffen:** `ingest/fetchers/*` (Fetcher), `data/build_db.py` (Loader),
  `data/run_ingest.py` + `data/orchestrate.py` (Ingest), `.github/workflows/`
  (Scheduler), Tests.
- **Hauptrisiko:** Format-Inkonsistenz Fetcher↔Loader führt zu stillen
  Datenverlusten (leere Lots), dazu 3 Häuser ohne Ingest, 2 ohne Loader, kein
  Scheduler, kein E2E-Test.
- **Betroffen:** Schema (DB-Shape bleibt), Workflow (Scheduler),
  Geschäftslogik (Normalisierung), keine Security-Änderung.

## 2. Established facts (aus dem Code belegt)

1. `run_provider` (`data/orchestrate.py:21`) ist generisch:
   `auth → discover → dedup → fetch → archivieren`. Manifest-Dedup
   (`ingest/registry.py:62`) funktioniert.
2. **FILE_PARSERS sind konsistent** (`data/parse_results.py`):
   `parse_weinauktionator_xlsx` und `parse_hdh_pdf` liefern `{auction, lots}`
   exakt wie `load_weinauktionator`/`load_hdh` es lesen. ✓
3. **Alle JSON-Fetcher liefern ein anderes Format als ihre Loader erwarten.**
   Belegt:
   - `dorotheum.py:44` liefert `lots` als **Dict** (`{uid: lot}`);
     `load_dorotheum` (`build_db.py:818`) iteriert `d.get("lots", [])` als Liste.
   - `pandolfini.py:75` liefert `auction{name,start_date,location}` +
     `lots{name,price,…}`; `load_pandolfini` (`:845`) erwartet
     `auction{id,name,date}` + `lots{lot_nr,estimate_low,estimate_high,
     sold_price{class,value}}`.
   - `winefields.py:64` liefert `auction{location_name,currency_code,…}`;
     `load_winefields` (`:612`) erwartet `auction{auction_id,title,time_start}`
     + `lots{lot_no,title,hammer,status,…}`.
   - `langtons.py:73` liefert `lots{lot_no,…}`; `load_langtons` (`:674`)
     erwartet `lots{lot,winning_bid,…}`.
   - `sothebys.py` (eben gebaut) liefert `lots{lot_no,hammer,…}`;
     `load_sothebys` (`:701`) erwartet `auction{auction_id,title,dates,currency,
     location}` + `lots{lot_number,hammer_price,final_price,sold}`.
   - `finarte.py:62`, `beschcannes.py:46`, `dobiaschofsky.py:35` liefern rohe
     Felder; ihre Loader (`:790`, `:642`, `:873`) erwarten andere Namen.
4. **Ingest-Lücken** (`data/run_ingest.py:21` `PROVIDERS`): `finarte`,
   `besch-cannes`, `dobiaschofsky` fehlen (Fetcher + Loader existieren aber).
5. **Loader-Lücken**: kein `load_koppe`; `load_steinfels` (`build_db.py:1036`)
   liest nur Alt-XLSX (`priceData/import/steinfels/prepared/*.xlsx`), nicht die
   Fetcher-JSON; kein `load_weinboerse`.
6. **Alt-Bestand ohne Fetcher** (nicht nachladbar): `baghera, christies,
   zacky, munich-wine-company, winebarrel, wermuth-sa`.
7. **Kein Scheduler**: nur `.github/workflows/ci.yml` existiert;
   `ingest.yml`/`process.yml` aus dem alten Bauplan (Step 6/7) fehlen.
8. **Tests**: 32 Unit-Tests decken Fetcher-Parsing (gemockt) + data ab.
   E2E-Test existiert nur für `weinauktionator`
   (`data/tests/test_orchestrate.py`).

## 3. Scope

**In Scope:** Format-Konsistenz der 12 fetchbaren Häuser herstellen, 3 Häuser
in Ingest aufnehmen, 2 Loader bauen, Scheduler, E2E-Test, Guardrails.

**Out of Scope:** Alt-Bestand ohne Fetcher (baghera, christies, zacky,
munich-wine-company, winebarrel, wermuth-sa) bleibt historisch. Kein neuer
Datenbestand, keine neuen Fetcher für weitere Häuser.

**Annahmen (aus dem Code bewiesen):** Normalisierung passiert im Fetcher
(`fetch` liefert das Loader-Format, Muster = `parse_results.py`); Loader bleiben
unverändert.

**Entscheidungen (vom User freigegeben):**
- **(D1)** idealwine läuft über `run_idealwine_delta.py` (direkt in DB,
  bewiesen funktionierend). `idealwine` wird aus `run_ingest.PROVIDERS`
  entfernt; kein eigener Ingest-Fetcher nötig. Fokus liegt auf den Daten, nicht
  auf der Fetcher-Implementierung.
- **(D2)** Sothebys läuft nur lokal (Turnstile blockiert Data-Center-IP), wenn
  bewiesen funktionierend — ist bestätigt.

## 4. Evolutionary micro-steps

**Step 1 — Kanonisches Format dokumentieren.** In `docs/` das `{auction, lots}`-
Shape + Feldnamen-Tabelle (Fetcher-roh → Loader-Feld) für alle 12 Häuser
festhalten. Referenz: `parse_results.py` + die Loader. Validierung: Review.
Fertig wenn die Tabelle für alle Häuser steht.

**Step 2 — Gruppe A normalisieren** (langtons, winefields, dorotheum,
pandolfini, sothebys): `fetch` mappt auf das Loader-Format (top-level
`auction`/`lots`, Feldnamen). Je Haus: Fixture-Test mit gemockter Antwort →
erwartetes normalisiertes JSON. **Zusätzlich hdh-Parser erweitern**
(`data/parse_results.py:parse_hdh_pdf`): `wine`, `grower`, `vintage`, `size`,
`estimate_low`/`estimate_high`, `mixed_lot`, `condition` extrahieren (Review-
Finding Step 1: `load_hdh` liest diese Felder, der Parser liefert sie nicht).

**Zusätzlich Verzeichnisname-Fix** (neues Finding): Orchestrator schreibt nach
`ARCHIVE/<provider>` (lowercase), Loader liest `ARCHIVE/<Haus>` (CamelCase).
Zentrales Mapping `provider → archive_dir` in `data/orchestrate.py` einführen,
damit Fetcher-JSONs im Loader-Verzeichnis landen (hdh→HDH, langtons→Langtons,
winefields→Winefields, dorotheum→Dorotheum, pandolfini→Pandolfini,
finarte→Finarte, besch-cannes→BeschCannes, dobiaschofsky→Dobiaschofsky,
sothebys→Sothebys; weinauktionator unverändert).

Validierung: `python -m unittest discover -s ingest/tests` + `data/tests`.

**Step 3 — Gruppe B normalisieren + in Ingest** (finarte, besch-cannes,
dobiaschofsky): wie Step 2, zusätzlich `PROVIDERS` in `run_ingest.py`
ergänzen. Validierung: Unit-Tests + `run_provider`-Smoke.

**Step 4 — Gruppe C Loader bauen** (koppe, weinboerse): `load_koppe` +
`load_weinboerse` in `build_db.py` (Muster = `load_langtons`/`load_pandolfini`),
`load_steinfels` um Fetcher-JSON ergänzen bzw. `load_weinboerse` neu.
Validierung: `build_db.py --dry-run --only koppe,weinboerse,steinfels`.

**Step 5 — PROVIDERS-Vollständigkeit + Dedup-Idempotenz:** alle fetchbaren
Häuser in `PROVIDERS`; prüfen, dass Manifest-Dedup Wiederholungsläufe idempotent
macht. Validierung: Unit-Test / `run_ingest`-artiger Lauf.

**Step 6 — Scheduler:** `.github/workflows/ingest.yml` (cron + workflow_dispatch,
`concurrency`, Secrets aus `${{ secrets.* }}`) + `.github/workflows/process.yml`
(materialize → build_db → build_wines). Validierung: workflow_dispatch-Testlauf.

**Step 7 — E2E-Test + Guardrails:** ein E2E-Test pro Haus-Gruppe (gemockte
Session) für `discover → dedup → fetch → archivieren → laden`; Fehler-Isolation
(ein Fetcher-Fail bricht nicht den Rest) + Job-Summary. Validierung: `data/tests`
+ `build_db --dry-run`.

## 5. Validation matrix

| Betroffenes | Validierung |
|---|---|
| Fetcher-Normalisierung | `python -m unittest discover -s ingest/tests -v` |
| Loader | `python3 data/build_db.py --dry-run` |
| Orchestrator/Dedup | `python -m unittest discover -s data/tests -v` |
| Scheduler | `workflow_dispatch`-Testlauf |
| Lint | super-linter (`.github/workflows/ci.yml`) |
| DB-Gates | `_validate_gates` (bereits in `build_db.py`) |

## 6. Risks and rollback

- **Stille Datenverluste durch Format-Mismatch:** Hauptrisiko. Mitigation:
  Fixture-Tests prüfen Feldnamen exakt; `--dry-run` zeigt Lot-Zahlen je Haus.
- **Duplikate:** Manifest-Dedup + `UNIQUE`-Constraints in `build_db.py`;
  Rollback = Manifest zurücksetzen + `build_db` neu.
- **Quellen-Bruch:** isolierter Fetcher-Fail, Job rot, Notification; idempotent.
- **Rollback:** alle Schritte sind additiv (neue Fetcher-Mappings/Loader);
  `git revert` des jeweiligen Commit reicht.

## 7. Approval gate

Freigegeben (D1, D2 bestätigt). Umsetzung schrittweise; nach jedem Step
`senior-code-review`, sämtliche Findings fixen.

---

## Progress

- [x] Step 1: Kanonisches Format dokumentieren
  - Evidence: `docs/ingest-format.md` erstellt; Senior-Review lief, alle Findings gefixt (hdh ⇧, price_basis-Enum, sothebys final_price als "zu bauen", dorotheum description, finarte currency, idealwine-Sonderweg). `python -m unittest discover -s ingest/tests` 32 OK, Pylint 10.00.
- [x] Step 2: Gruppe A normalisieren (langtons, winefields, dorotheum, pandolfini, sothebys) + hdh-Parser erweitern
  - Evidence: 5 Fetcher liefern jetzt `{auction, lots}` im Loader-Format; `parse_hdh_pdf` extrahiert `vintage/wine/estimate_low/estimate_high`; `ARCHIVE_DIRS`-Mapping in `orchestrate.py` (nur Gruppe A + hdh). Senior-Review lief, Findings gefixt: (HIGH) Gruppe-B aus `ARCHIVE_DIRS` entfernt, (MEDIUM) `_parse_price` europ. Zahlenformat, (LOW) Docs aktualisiert. Loader-Roundtrip-Test `data/tests/test_loader_roundtrip.py` (5 Häuser). `python -m unittest discover -s ingest/tests` 32 OK + `-s data/tests` 82 OK, Pylint 10.00. Commit `52bdb7a`.
- [ ] Step 3: Gruppe B normalisieren + in Ingest (finarte, besch-cannes, dobiaschofsky)
- [x] Step 3: Gruppe B normalisieren + in Ingest (finarte, besch-cannes, dobiaschofsky)
  - Evidence: 3 Fetcher liefern `{auction, lots}` im Loader-Format; besch-cannes lädt je Lot die Detail-Seite (`/en-lots/{id}`); `ARCHIVE_DIRS` + `_json_filename`-Patterns (auction-/auktion-*.json); `idealwine` aus PROVIDERS entfernt. Senior-Review lief, Findings gefixt: (MEDIUM) veralteter Docstring + dobiaschofsky Auktions-Ref `A###` in description bewahrt, (LOW) finarte `sold` bool+string, `_lot_id`/`_year` geankert. Orchestrator-Mapping-Test ergänzt. `-s ingest/tests` 33 OK + `-s data/tests` 86 OK, Pylint 10.00. Commit `52f1806`.
- [x] Step 4: Gruppe C Loader bauen (koppe, weinboerse)
  - Evidence: `load_koppe` + `load_weinboerse` (+ `_load_weinauktion_json`) gebaut; koppe/weinauktion-Fetcher normalisiert; `load_steinfels` lädt Alt-XLSX + API-JSON. Senior-Review lief, Findings gefixt: (HIGH) `koppe→Koppe` in `ARCHIVE_DIRS`, (MEDIUM) `--limit`-Restbudget bei steinfels, (LOW) disjunkte-Namensräume-Kommentar. Orchestrator-Mapping-Test um koppe ergänzt. `-s ingest/tests` 33 OK + `-s data/tests` 88 OK, Pylint 10.00. Commit `831ba04`.
- [ ] Step 5: PROVIDERS-Vollständigkeit + Dedup-Idempotenz
- [ ] Step 5: PROVIDERS-Vollständigkeit + Dedup-Idempotenz
- [ ] Step 6: Scheduler (ingest.yml + process.yml)
- [ ] Step 7: E2E-Test + Guardrails
