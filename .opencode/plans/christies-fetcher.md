# Bauplan: Christie's-Fetcher (Wein-Auktionen nachladen + CI)

## 1. Summary

- **Gewünscht:** Christie's in die Nachlade-Kette aufnehmen: Fetcher
  (`discover` → `fetch` → kanonisches Format), Tests, Ingest-Integration,
  automatische CI-Execution und Vollständigkeits-Guardrails inkl.
  Reconciliation.
- **Betroffen:** neuer `ingest/fetchers/christies.py`, `data/run_ingest.py`,
  `data/orchestrate.py` (`ARCHIVE_DIRS`), Tests, `.github/workflows/ingest.yml`.
- **Hauptrisiko:** stiller Teil-Import durch Pagination (nur erste Lots-Seite),
  falsche Währung, kommende Auktionen ohne Preise, falscher Wein-Kategorie-Filter.
- **Betroffen:** Workflow (CI), Geschäftslogik (Normalisierung), kein
  Schema-/Security-Impact.

## 2. Established facts (live verifiziert)

1. `load_christies` existiert (`data/build_db.py:729`) und erwartet
   `auction{event_id|sale_id, title, year, month, landing_url, location}` +
   `lots{lot_number, title, estimate_low, estimate_high, price_realised,
   lot_withdrawn, currency, description, url}`.
2. **Kein Fetcher** vorhanden; nicht in `PROVIDERS`; kein `ARCHIVE_DIRS`-Eintrag.
3. **Zugänglich ohne Cloudflare-Block** (status 200; kein Turnstile/camoufox/
   Login — deutlich einfacher als Sothebys).
4. **discover:** `/en/results` → Auktions-Links `/en/auction/auction-{sale_id}`;
   Wein-Abteilung = „Wine and Spirits" (`/en/departments/wine-and-spirits`).
5. **fetch:** `/en/auction/auction-{sale_id}` enthält ein eingebettetes JSON
   `"lots":[{…}]` (serverseitig) plus auction-Meta.
6. **Pagination (kritisch) + Reconciliation-Quelle:** `auction-31122` hat
   **860 Lots**, das eingebettete JSON liefert nur 84. Die vollständige Liste
   kommt von der **`lotsearch`-API**:
   `GET https://www.christies.com/api/discoverywebsite/auctionpages/lotsearch`
   mit `{language, pagesize, geocountrycode, saleid, salenumber, saleroomcode,
   page, filterids, searchphrase}` + Header `Accept: application/vnd.christies.v2+json`.
   Antwort: `{"lots":[…], "total_hits_filtered": 860}`. `total_hits_filtered`
   ist die erwartete Gesamtzahl (Reconciliation) und `page`/`pagesize` die
   Pagination.
7. **Lot-Felder (bewiesen):** `lot_id_txt` (Lotnr, 1..N), `title_primary_txt`
   (Wein), `title_secondary_txt` (Beschreibung), `estimate_low/high`,
   `price_realised`, `lot_withdrawn`, `url`, `estimate_txt`/`price_realised_txt`
   (Währungs-Präfix, z. B. „HKD …").
8. **auction-Meta (bewiesen):** `sale_id` („31122"), `title`, `sale_location`
   („HongKong"), `sale_number`, `auction_status.start_date`, `url`.

## 3. Scope

**In Scope:** Fetcher + Mapping auf `load_christies`, Pagination (alle Lots),
Fixture-/Loader-Tests, Ingest-Integration (`PROVIDERS`, `ARCHIVE_DIRS`,
`--only`), CI-Execution, Vollständigkeits-Guardrails inkl. Reconciliation.

**Out of Scope:** Alt-Bestand-Migration, Login/Auth, Schema-/Resolution-Änderungen.

**Nicht-funktionale Anforderungen (Guardrails):**
- **NFR-1 Fail-loud:** leeres Ergebnis (kein `lots` / leere `lots`) →
  übersprungen + geloggt, nicht als „gefetcht" markiert (bestehender Guard).
- **NFR-2 Pagination-Vollständigkeit:** **alle** Lots laden (nicht nur die erste
  Seite) über die „Load more"-API bis zur Gesamtzahl.
- **NFR-3 Sold-Erkennung:** `sold` nur wenn `price_realised` vorhanden **und**
  `lot_withdrawn` falsch.
- **NFR-4 Währung:** aus `estimate_txt`/`price_realised_txt` extrahiert
  (ISO-Präfix), nicht hartkodiert.
- **NFR-5 Idempotenz:** Manifest-Dedup; Wiederholungslauf lädt nichts erneut.
- **NFR-6 CI:** `ingest.yml` `--only` enthält `christies`; `process.yml` baut DB.
- **NFR-7 Reconciliation (approximativ):** die extrahierte Lot-Anzahl muss der
  Gesamtzahl („N lots" im HTML) entsprechen; Abweichung → Fehler/Warnung in der
  Job-Summary, damit Teil-Importe sichtbar werden.

## 4. Evolutionary micro-steps

**Step 1 — Fetcher-Gerüst + discover.** `ingest/fetchers/christies.py`:
`discover(session)` lädt `/en/results`, extrahiert `/en/auction/auction-{sale_id}`-
Links gefiltert auf „Wine and Spirits", dedup, `AuctionRef(provider="christies",
auction_id=sale_id, url=…)`. Muster = `dorotheum.py`. Validierung: Fixture-Test.

**Step 2 — fetch + Lot-Mapping.** `fetch(session, ref)` lädt die Auktions-Seite,
`raw_decode` des `"lots":[…]`-JSON, mappt auf `{auction, lots}` im `load_christies`-
Format + auction-Meta (event_id←sale_id, title, year/month←start_date,
landing_url, location←sale_location). Validierung: Fixture-Test.

**Step 3 — Pagination + Reconciliation (NFR-2, NFR-7).** Alle Lots laden (die
„Load more"-API `lotsearch` bis zur Gesamtzahl „N lots"); Reconciliation: extrahierte
Anzahl = Gesamtzahl, sonst Fehler/Warnung. Validierung: Fixture-Test mit
mehreren Seiten + Abweichungsfall.

**Step 4 — Loader-Roundtrip.** `data/tests/test_loader_roundtrip.py` um
`test_christies` ergänzen.

**Step 5 — Ingest-Integration.** `orchestrate.ARCHIVE_DIRS["christies"]="Christies"`;
`run_ingest.PROVIDERS` + `ingest.yml` `--only` um `christies` ergänzen.

**Step 6 — Senior-Review + Fixes.** alle Findings beheben.

## 5. Validation matrix

| Betroffenes | Validierung |
|---|---|
| Fetcher/Discover/Fetch | `python -m unittest discover -s ingest/tests -v` |
| Pagination + Reconciliation | Fixture-Test (mehrere Seiten + Abweichung) |
| Loader-Roundtrip | `python -m unittest discover -s data/tests -v` |
| DB-Reproduzierbarkeit | `python data/build_db.py --dry-run` |
| Idempotenz | `test_runs_idempotent`-Muster |
| CI | `workflow_dispatch` auf `ingest.yml` |
| Lint | Pylint (`ingest/`, `data/`) |

## 6. Risks and rollback

- **Teil-Import (Pagination):** NFR-2 + NFR-7 + Fixture-Test.
- **Falsche Währung:** NFR-4 + Roundtrip-Assert.
- **Kommende Auktion ohne Preise:** NFR-1/NFR-3.
- **Rollback:** additiv (neuer Fetcher + Mapping), `git revert` genügt.

## 7. Approval gate

Freigegeben; Reconciliation (NFR-7) nachträglich aufgenommen.

---

## Progress

- [x] Step 1: Fetcher-Gerüst + discover
  - Evidence: `christies.py` discover filtert über `followAnalyticsMetadata` auf Wine & Spirits (live verifiziert: 1 Wein-Auktion 31122). Commit `e9eb972`.
- [x] Step 2: fetch + Lot-Mapping
  - Evidence: lotsearch-API + Mapping auf `load_christies`-Format. Commit `e9eb972`.
- [x] Step 3: Pagination + Reconciliation
  - Evidence: `_all_lots` paginiert bis `total_hits_filtered`, `RuntimeError` bei Abweichung/fehlendem total. Live verifiziert: 860 Lots (11 Seiten). Commit `98ba774`/`526de7c`.
- [x] Step 4: Loader-Roundtrip
  - Evidence: `test_christies` in `test_loader_roundtrip.py` (1/1 hammer+wein). Commit `2bdddee`.
- [x] Step 5: Ingest-Integration
  - Evidence: `ARCHIVE_DIRS["christies"]="Christies"`, `PROVIDERS` + `ingest.yml --only` um christies. Commit `2bdddee`.
- [x] Step 6: Senior-Review + Fixes
  - Evidence: 2 Review-Runden, alle Findings gefixt (Infinite-Loop, Reconciliation, Meta raw_decode→gezielte Regex, Wein-Filter, total-None fail-loud, Orchestrator pro-auction fetch-guard). Live E2E verifiziert. `-s ingest/tests` 35 OK + `-s data/tests` 92 OK, Pylint 10.00.
