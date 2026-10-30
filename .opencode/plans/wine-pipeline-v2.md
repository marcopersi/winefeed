# Bauplan: Wein-Daten-Pipeline v2 (Referenz: VinoImporter-Zielstruktur)

> **Status:** Review + Ergänzung (Senior-Engineering-Durchsicht). Der Rumpf wurde
> gegen den tatsächlichen Code-Stand geprüft. Dieser Plan **löst
> `wine-lot-normalization-llm.md` ab** (dessen „alle 2,77 Mio Lots per LLM"-Ansatz
> ist zu teuer und widerspricht dem Deterministik-Prinzip, siehe §4) und ist der
> Daten-Unterbau für `wine-mvp-search-chart.md` (#94: Suche + Preis-Chart).

---

## Leitmotiv (was die Lösung erreichen soll)

**Geschäftsziel:** Für jeden realen Wein eine belastbare **Preis-Zeitreihe über
alle Auktionshäuser hinweg** zeigen — vergleichbar gemacht über Jahrgang,
Gebinde, Währung und Aufgeld. Das setzt voraus, dass dieselbe Flasche, egal wie
12 Häuser sie beschreiben, auf **eine** kanonische Wein-Identität zusammenläuft.

**Die Normalisierung ist das Kernstück** — alles andere (Chart, Suche, Facetten)
ist wertlos, wenn „Ch. Montrose", „Château Montrose 2015" und „Montrose, St-
Estèphe (6 BT)" nicht auf denselben Wein + getrennte Attribute (Jahrgang,
Gebinde, Anzahl) abbilden.

**Erfolgskriterien (messbar, in `build_metrics` zu führen):**

- **Coverage:** Anteil SINGLE-Lots mit `wine_ref_id IS NOT NULL` (heute fallen
  AMBIGUOUS-Lots still heraus, siehe §4.0). Zielgröße nach Baseline festlegen.
- **Precision auf dem Gold-Set:** ≥ X % korrekte (Wein, Jahrgang, Gebinde)-
  Zuordnung auf einer handgelabelten Stichprobe (§4, Eintrittsbedingung).
- **LLM-Anteil:** Anteil **distinkter Aliasse** (nicht Lots!), die lokal nicht
  aufgelöst werden und an den LLM gehen — soll klein und sinkend sein.
- **Determinismus:** Zwei Builds aus identischem Input ⇒ identische DB
  (bereits durch `test_repeatability.py` abgesichert).

---

## Bestandsaufnahme (was es schon gibt — NICHT neu bauen)

Der Rumpf liest sich, als werde bei Null begonnen. Tatsächlich existiert eine
reife, versionierte Pipeline. v2 **erweitert/konsolidiert**, ersetzt nicht.

| Bereich | Vorhanden (Datei) |
|---|---|
| Matching-Key | `wine_resolution/normalize.py` (NFKD, lower, `ch→chateau`) |
| Jahrgang | `wine_resolution/vintage.py` (8 Status: STRUCTURED/EXTRACTED/NV/MV/MISSING/AMBIGUOUS/CONFLICT/INVALID) |
| Gebinde/Anzahl | `wine_resolution/bottle.py` (`(6 BT)` → qty + `bottle_size_dl`) |
| Mixed-Lots | `wine_resolution/mixed_lots.py` (provider-flag/keyword/multi-wine/multi-vintage) |
| Alias-Resolution | `wine_resolution/resolver.py` (AMBIGUOUS statt „first-wins") |
| Kanon. Name | `wine_resolution/canonical.py` (Diakritika > Nicht-CAPS > Evidenz) |
| Herkunft (Geo) | `wine_resolution/origin.py` + `wine_origins` (22-spaltig, multilingual) |
| Rebsorte | `wine_resolution/variety.py` + `reference/varieties.csv` |
| Spirituosen-Filter | `wine_resolution/spirits.py` + `reference/spirits_terms.csv` |
| Kuratierung | `reference/wine_alias_overrides.csv` (MERGE, `action`/`reason`) |
| **DeepSeek-Tooling** | `review_producer_extraction.py` (offline split) + `llm_review_producer.py` (deepseek-flash, batched, resumable, JSON-mode, 429-Retry) → `wine_llm_overrides.csv` / `wine_llm_rest.csv` |
| Provenienz | `builds` / `build_inputs` / `build_metrics`, `*_version`-Konstanten |

**Deine DeepSeek-Beispiele sind im Code angekommen:** `llm_review_producer.py`
ist genau das Muster — deutscher System-Prompt, `temperature=0`,
`thinking disabled`, JSON-`response_format`, parallele Batches, `.state`-Resume.
v2 verallgemeinert dieses Muster zur **generischen LLM-Residuen-Stufe** (§4.4).

---

## 0. Zielstruktur (Referenz, verbindlich)

Aus `VinoDomain` (`Wine`, `Unit`, `Offering`, `WineOffering`, `Origin`, `Rating`)
und dem Steinfels-Staging-File abgeleitet. **Die Python-`wines`/`lots`-Schemata
sind bereits ein Superset des Java-Modells** (Mapping-Tabelle in §5).

- **Wine** (der Wein): `name`, `origin`, `producer`, `region`, `vintage`.
  - `origin` ist in `VinoDomain` ein **Enum** (`AC/MC`, `MO/DOC`, `MO/DOCG`,
    `MO/IGT`, …) = eine **Qualitäts-/Rechts-Klassifikation**, nicht die
    Geografie. **Achtung — Modell-Klärung:** Das bildet in der Python-DB auf
    `lots.classification` / `wines.classification` ab, **nicht** auf die
    geografische Referenz `wine_origins` (Land/Region/Appellation). Beide
    Konzepte getrennt halten.
  - `producer` = Produzent (Tenuta San Guido …).
  - `name` = reiner Wein-Name (ohne Produzent, ohne Jahrgang, ohne Gebinde).
- **Unit** (Gebinde): `deciliters` (3.75 / 7.5 / 15 / 30 / 45 / 60 …).
- **Offering** (Lot): `provider`, `providerOfferingId` (= Losnummer),
  `priceMin`/`priceMax` (= Schätzung), `offeringDate`, `realizedPrice`, `isOHK`,
  `note`, `eventIdentifier`, `noOfBottles`.
- **Origin-Enum**: s. o. (Klassifikation). **Geografie** liegt separat in
  `wine_origins`.
- **Rating/RatingAgency**: Parker (100), Gabriel (20), Weinwisser (100),
  Falstaff (100). **Gap:** In der Python-DB gibt es aktuell **keine** Rating-
  Tabelle. **Entschieden:** Ratings sind **nicht** Teil des MVP — als
  separates Issue zurückgestellt (braucht eine Rating-Quelle).

Flache Serialisierung (= Staging-File, `WineOffering.toXLSString()`):
`providerOfferingId; name; origin; producer; region; vintage; noOfBottles; deciliters; isOHK; priceMin; priceMax; realizedPrice`

---

## 1. Scraping (Quellen)

- **Status:** `ingest/`-Fetcher (12 Häuser CI + sothebys lokal) vorhanden; Archiv
  auf Samsung (`ARCHIVE_PATH`-Default ist veraltet, siehe `AGENTS.md`).
- **Offene Fragen:** Quell-Referenz je Haus; Christie's-Backfill
  (`run_christies_backfill.py`); PDF-Häuser (Denz/Wermuth-Alt via `VinoImporter`
  iText-Parser).

## 2. Historische Daten vollständig erfassen (PFLICHT)

**⚠ Befund aus der Review — die Staging-Files sind deutlich grösser als im Rumpf
angenommen (Multi-Event-Workbooks mit uneinheitlichem Schema):**

- `data/vinoStagingFileSteinfels.xlsx`: **3 Sheets** — `Steinfels_04.05.2002`
  (833 Z.), `Steinfels_05.03.2016` (516 Z.), `nonRecordLines` (521 Z., kein
  Record-Sheet → ausschliessen). ⇒ **zwei** Steinfels-Events, nicht eines.
  Header (16 Sp.): `name, origin, producer, region, vintage, deciliters,
  eventIdentifier, isOHK, noOfBottles, providerOfferingId, note, offeringDate,
  priceMin, priceMax, realizedPrice, provider`.
- `data/vinoStagingFile2015-2008.xlsx`: **42 Sheets** — ein `Wermuth SA.`-Event
  je Sheet (2008-02-28 … 2015-11-14), ~30–40k Zeilen gesamt. **Die Spaltenzahl
  variiert je Sheet (12 / 14 / 16 / 17)** — der Import braucht **Header-basierte
  Spaltenerkennung pro Sheet**, keinen festen Index. Beispiel-Header (12 Sp.):
  `providerOfferingId, name, producer, vintage, noOfBottles, deciliters, isOHK,
  priceMin, priceMax, realizedPrice, provider, eventIdentifier`.

⇒ **Import-Schritt ist eine Event-Schleife** (Sheet = Auktion = `eventIdentifier`),
mit Header-Mapping pro Sheet, `nonRecordLines` übersprungen. Nicht ein `wb.active`.

Noch nicht verarbeitete Quellen (vom Auftraggeber bereitgestellt):

- [x] `data/vinoStagingFileSteinfels.xlsx` (2 Events: 2002 + 2016) — via
      `load_steinfels_staging`.
- [x] `data/vinoStagingFile2015-2008.xlsx` (42 Wermuth-Events 2008–2015) — via
      `load_wermuth`.
- [x] `VinoImporter/validatedOutput/output_WermuthSA_*.csv` (2014–2018) — via
      `load_wermuth_validated`. **Die hier geforderte
      Überschneidungsprüfung wurde ursprünglich NICHT gemacht** (beide Loader
      liefen, ohne gegeneinander zu prüfen) — direkt an der Live-Master-DB
      verifiziert und gefixt, s. Commits "wire up producer/wine matching"
      (Kapitel 4.2–4.3-Eintrag) ff.: 4 echte Terminüberschneidungen
      (2014-12-04, 2015-03-14, 2015-06-06, 2015-11-14, identische Lot-Nummern/
      Weine/Preise unter unterschiedlichen `auction_id`s) + zwei openpyxl-
      Artefakte (Used-Range-Überhang → hunderte Blank-Rows; eine
      „Total: X CHF"-Zeile pro Sheet ohne Weinnamen) in `load_wermuth` /
      `load_steinfels_staging`. Alle drei gefixt, zweifach gegen die reale DB
      verifiziert (Rebuild → Rebuild): 2.787.793 → 2.784.499 → 2.783.740 Lots,
      0 doppelte wermuth-sa-Termine, 0 AMBIGUOUS, `integrity_check` ok.
- [x] Steinfels-PDF-Quellen (`priceData/import/steinfels/source/*.pdf`, 10
      Dateien) — Abgleich gegen `results_*.xlsx`/Staging ergab: 315, 317
      (als `317_direct`), 319, 320–324 bereits abgedeckt; 379 bereits über
      `load_steinfels_staging` abgedeckt (Event `Steinfels_05.03.2016`,
      identisch mit `VinoImporter/import/Steinfels/379_05032016_Resultate.pdf`);
      `VinoImporter/import/Steinfels/315.pdf` ist dasselbe PDF wie
      `source/2002/315.pdf`, ebenfalls bereits abgedeckt. **318 war die
      einzige echte Lücke** — `results_318.xlsx` existierte nicht, keine
      DB-Auktion. Grund: 318.pdf hat keine Textebene (3060 Vektorkurven/
      Seite, keine echten Zeichen im Body) im Gegensatz zu allen anderen
      2002/2003-Dateien — nie extrahiert worden (der archivierte
      `parser_318.py`-Stub war ein nicht lauffähiger Platzhalter mit
      ungültigem `2003.320`-Import). Gefixt via OCR-Extraktion
      (`data/extract_steinfels_318.py`: 300dpi-Render + tesseract, Korrektur
      der schrift-systematischen OCR-Verwechslungen dieser PDF — 696/702
      Zeilen geparst, 99.1%) → `results_318.xlsx`, vom bestehenden
      `load_steinfels()`-Glob-Loader ohne Codeänderung aufgenommen.
      **Zwei weitere Altbugs dabei gefunden und gefixt:** `results_316.xlsx`
      (531 Lots) dupliziert das Staging-Event `Steinfels_04.05.2002` (832
      Lots) — identischer Lot 1 ("Valandraud" 1998, CHF 1850) in beiden,
      Staging-Version vollständiger; Datei beim Laden übersprungen.
      `bottle_size_dl` wurde aus einer Spalte `Unit_DL` gelesen, die nur in
      315/316 existiert — 317/319–324 speichern denselben Dezilitern-Wert
      direkt unter `Unit`, war also für 7 von 9 Dateien dauerhaft `NULL`;
      jetzt werden beide Spaltennamen geprüft. Rebuild verifiziert:
      2.783.740 → 2.783.905 Lots (+165 = +696 aus 318, −531 aus 316-Dedup),
      694/696 neue 318-Lots auf einen canonical wine aufgelöst, 0
      AMBIGUOUS, `bottle_size_dl` jetzt für alle 10 Steinfels-Auktionen
      gefüllt, `integrity_check` ok.
- [x] `VinoImporter/import/Steinfels/315.pdf` + `379_05032016_Resultate.pdf`
      — s.o., beide bereits abgedeckt, keine neue Arbeit nötig.
- [x] **Weinbörse** (`priceData`-Archiv `Weinboerse/**/Resultfile*.json`,
      840 Dateien, 2020–2026): `load_weinboerse` zeigte **1 Auktion / 0
      Lots** — sah nach „erledigt" aus, war aber leer. Ursache:
      `load_weinboerse` rief `_load_weinauktion_json` mit dem **falschen
      JSON-Schema** auf (erwartet `{auction, lots}`; der reale Export ist
      `{"@related": {auctions, catalogs, parts}, "items": [...]}`) **und**
      dem falschen Verzeichnis-Case (`weinboerse` vs. real `Weinboerse` —
      funktioniert nur auf macOS case-insensitive, nicht auf Linux-CI).
      Neuer Parser für das Freitext-`description`-HTML-Feld geschrieben
      (Produzent/Kategorie-Split, Region+Farbe aus der Kategorie,
      Menge+Gebinde inkl. Bruch-Notation `"12 3/8 Flaschen"` = 12×0.375L,
      explizite Literangaben `"1 Jeroboam 5L"` überschreiben den
      Format-Default, OHK-Erkennung, Mixed-Lot-Heuristik die echte
      Zweitweine von Zustands-Rauschen wie `"4x befleckt, 1x defekt"`
      unterscheidet) — 12.312/12.312 Lots geparst, 0 Fehler, zwei
      Advisor-Runden mit echten Funden (OHK-Regex ohne Wortgrenze traf
      `"Ockfener Bockstein"`/`"...MEDOC"`; Mixed-Lot-Heuristik verwechselte
      Zustandscodes wie `"HS/TS"` mit echten Zweitweinen; am Ende noch ein
      `re.IGNORECASE`-Regression, die `"Pays d'Oc"` fälschlich als OHK
      markiert hätte — alle per Test abgesichert).
      **Zwei weitere, unabhängige Altbugs gefunden:** `_load_weinauktion_json`
      erzeugte für jede Datei ohne `{auction, lots}`-Schema eine
      Phantom-Auktion mit `auction_id="None"` (0 Lots) statt die Datei zu
      überspringen — betraf **auch Steinfels** (daher „10
      Steinfels-Auktionen" oben **jetzt 11**, nach Entfernen des Phantoms;
      Lots unverändert). `ingest/fetchers/weinauktion.py`s `_map_lot` warf
      das rohe `description`-HTML weg und behielt nur einen geflatteten
      Blob ohne Produzent/Menge/OHK — jetzt zusätzlich erhalten (vom
      Loader aktuell ungenutzt, für einen späteren volleren Reparse).
      **Für den laufenden CI-Monats-Job** (`ingest.yml` holt `weinboerse`
      bereits monatlich) zwei Dinge ergänzt: der Fallback-Aufruf auf
      `_load_weinauktion_json(b, "weinboerse", …)` für künftig gefetchte
      Dateien (ging beim Neuschreiben des Loaders verloren, da sonst nie
      wieder etwas einträfe) und ein Dedup-Schutz gegen Doppel-Import,
      falls der Fetcher eine Auktion erneut holt, die der historische Dump
      schon abdeckt (Katalog-IDs partitionieren sich nicht sauber von den
      Auktions-IDs — 168→167, 202→200 im realen Archiv). Rebuild
      verifiziert: 2.783.905 → 2.796.217 Lots (+12.312), 15
      Weinbörse-Auktionen, 0 Phantom-Auktionen (global), 0 AMBIGUOUS, die
      bestehenden 8.690 SINGLE-ohne-`wine_ref_id` unverändert,
      `integrity_check` ok, 0 falsch-positive `is_ohk`-Treffer (per Skript
      gegen alle Rohbeschreibungen verifiziert).
      **Lehre:** der ursprüngliche `test_loader_roundtrip.py::test_weinboerse`
      bestand, weil seine Fixture zufällig zum (ungenutzten)
      Fetcher-Output-Schema passte, nicht zum tatsächlich archivierten
      Rohformat — ein grüner Loader-Test beweist nicht, dass der Loader
      die *reale* Quelle liest. Für Denz/sylvies/weinauktionator (s.u.)
      vor dem Schreiben eines Loaders immer zuerst eine echte Stichprobe
      aus dem Archiv parsen, nicht nur gegen eine erfundene Fixture testen.

**Noch offene, bisher nirgends dokumentierte Lücken** (beim
Weinbörse-Review entdeckt, nicht Teil der ursprünglichen Bestandsaufnahme):

- [ ] **Denz** (`WeinAuktionspreise/Denz/`, PDFs 2003–2026): kein Loader in
      `build_db.py`, keine Einträge in der Provider-Tabelle. In Kapitel 1
      nur als „offene Frage" erwähnt (`VinoImporter`-PDF-Parser), nie
      begonnen.
- [ ] **sylvies** (`WeinAuktionspreise/sylvies/`, Zip-Archive 2012–2026):
      kein Loader. Es liegt dort bereits ein `sylviesParser.py` /
      `sylviesParser2022.py` — beide nur stdout-Scraping-Prototypen ohne
      Persistenz, keine DB-Anbindung.
- [x] **weinauktionator** — **war kein CI-Leak, nur ein Backlog, der die
      Pipeline nie durchlaufen hat.** Die Pipeline selbst
      (`WeinauktionatorFetcher` → `orchestrate._store_parsed` →
      `parse_weinauktionator_xlsx` → flaches JSON → `load_weinauktionator`)
      ist korrekt — geprüft gegen alle 30 archivierten `.xlsx`-Dateien
      (nicht 60: 30 `.xlsx` + 30 `.pdf`, dieselben Auktionen in zwei
      Formaten), 0 Parse-Fehler, 99,3 % `lot_kind=SINGLE`. Grund für „0
      Lots": die 30 `.xlsx`-Dateien (alle mit identischem mtime-Batch
      16.08.2026 — ein einziger händischer Download, nicht Fetcher-Output)
      wurden nie durch `parse_weinauktionator_xlsx` geschickt; der Fetcher
      persistiert ohnehin nie die rohe xlsx, nur das Parse-Ergebnis. Fix:
      `data/backfill_weinauktionator_json.py` (neu, Präzedenz:
      `extract_steinfels_318.py`) — ruft denselben Live-Parser auf 30
      Dateien auf, schreibt das JSON **flach** (exakt `_write_json`s
      Konvention, keine Unterordner — eine erste, naive Version landete
      in Unterordnern und hätte beim ersten echten CI-Refetch jede
      Auktion doppelt geladen, derselbe Bugklasse wie unten). Rebuild
      verifiziert: 2.796.217 → 2.804.014 Lots (+7.797), 30
      Weinauktionator-Auktionen, 0 Phantom-Auktionen, 0 AMBIGUOUS, die
      bestehenden 8.690 SINGLE-ohne-`wine_ref_id` unverändert,
      `buyer_premium`/`tax_amount` jetzt erstmals für diese 5.150
      verkauften Lots abgeleitet, `integrity_check` ok. **Nicht
      vollständig:** Auktions-IDs 23 und 27 fehlen im Archiv (abgesagt
      oder nie heruntergeladen) — ein künftiger CI-Lauf kann diese plus
      neuere Auktionen ergänzen.
- [ ] **Cross-cutting: zwei getrennte, nie abgeglichene Archive.**
      Beim weinauktionator-Review entdeckt, betrifft potenziell alle 12
      CI-Häuser: `ingest.yml` schreibt NICHT in den Samsung-Pfad, sondern
      in ein GitHub-Actions-**Artifact** (`auction-archive`,
      `runner.temp`), das `process.yml` danach lädt, um sein eigenes
      DB-Artifact zu bauen. Das Manifest (`data/ingest_manifest.json`)
      zeigt einen echten CI-Lauf am 11.10.2026, der Weinauktionator
      34–39 gefetcht hat — in dieses Artifact, nicht auf die
      Samsung-Disk (dort lagen 34–39 bereits seit dem 16.08.2026-Batch,
      rein zufällig). Das bedeutet: **das CI-`process.yml`-DB-Artifact
      ist strukturell unvollständig** — es enthält nie die
      händisch-auf-Samsung-platzierten Quellen (Weinbörse-840-Resultfiles,
      die 30 Weinauktionator-JSONs, Steinfels-xlsx unter `priceData/`,
      beide `vinoStagingFile*.xlsx`). Umgekehrt landet alles, was CI
      monatlich frisch fetcht, nie auf der Samsung-Disk, die dieser
      Bauplan und `build_db.py` lokal als „die" Produktions-DB behandeln.
      **Entscheidung beim Auftraggeber nötig** (keine davon ist rein
      technisch, alle sind grösser als ein einzelnes Haus):
      (a) CI-Artifact periodisch herunterladen und auf Samsung mergen,
      (b) das CI-DB-Artifact als kanonisch behandeln und den
      Samsung-Workflow auslaufen lassen, oder (c) neue Archiv-Dateien aus
      `ingest.yml` direkt ins Repo committen statt als Artifact.
- [ ] **Generischer Dublettenschutz für „zwei Quellen, eine Auktion"** —
      vierter Fall dieser Bugklasse in dieser Session (Wermuth xlsx/CSV,
      Steinfels 316/Staging, Weinbörse Dump/Fetcher, jetzt
      Weinauktionator Backfill-Pfad). Jedes Haus mit zwei Quellen
      (Dump + Fetcher, xlsx + CSV) braucht ein Äquivalent zu
      `_wermuth_xlsx_dates`, und ein `--only <house>`-Lauf sollte
      `COUNT(DISTINCT lot_no) == COUNT(*)` pro Auktion als Gate prüfen.
      Noch nicht umgesetzt — Kandidat für einen späteren generischen Pass
      statt Haus-für-Haus-Wiederholung.

**Prüfschritt (ausführen, sobald Samsung gemountet — aktuell nicht gemountet):**
Abgleich, welche Events schon in der Master-DB sind, statt Annahme:

```sql
-- Sind Steinfels/Wermuth-Events schon drin? (0 ⇒ echte Lücke)
SELECT p.name, a.auction_id, a.auction_date, COUNT(*) AS lots
FROM lots l JOIN auctions a ON l.auction_id=a.id
JOIN providers p ON a.provider_id=p.id
WHERE p.name IN ('Steinfels','Wermuth SA.','WermuthSA','Wermuth')
GROUP BY 1,2,3 ORDER BY 1,3;
```

Dublettenschutz ist durch `source_record_hash` / `source_lot_key` bereits
vorgesehen — der Import muss diese füllen, damit ein Re-Run idempotent bleibt.

## 3. Referenzlisten (Grundlage der Normalisierung)

**Teilweise vorhanden** — nur die echten Lücken neu anlegen:

| Liste | Status |
|---|---|
| Herkunft (Geo) | ✅ `wine_origin_reference_multilingual.csv` + `wine_origin_input_mapping.csv` |
| Rebsorten | ✅ `reference/varieties.csv` |
| Spirituosen-Ausschluss | ✅ `reference/spirits_terms.csv` |
| Alias-Kuratierung | ✅ `reference/wine_alias_overrides.csv` |
| **Produzenten** (`producers.csv`) | ❌ **neu** — kanonisch + Aliase; heute nur implizit in Overrides |
| **Weine je Produzent** (`wines_by_producer.csv`) | ❌ **neu** — z. B. Bernhard Huber → Malterdinger Spätburgunder, Wildenstein R GG, Hecklinger Schlossberg R GG, Bienenberg … |
| **Gebinde** (`units.csv`) | ◐ Logik in `bottle.py`; als gepflegte CSV externalisieren (dl + Label + Aliase) |
| **OHK** (`ohk.csv`) | ❌ **neu** — ohk, oc, owc, cbo, caisse bois + Varianten → `is_ohk` |
| Jahrgänge | ◐ Regex in `vintage.py` (1700–2099; CHECK bis 2100); eigene Liste unnötig |

**Policy-Festlegung (jetzt explizit + im Code konsistent, s. Kapitel 4.2–4.3
im Progress-Log):** Namens-Priorität in `_resolve()` ist **curated Override >
idealwine > auto** — ein `MERGE`-Override ist eine menschliche Entscheidung zu
genau diesem Alias und schlägt die automatische idealwine-Referenz (konsistent
mit §4.5: „CURATED = höchste Vertrauensstufe, nie vom Auto-Resolver
überschrieben"). Vorher stand hier fälschlich „idealwine höchste Priorität vor
Overrides" — das beschrieb nie den tatsächlichen Code (der Name folgte schon
immer `forced`-zuerst; nur das `canonical_source`-Label behauptete das
Gegenteil, s. Review-Befunde #2). **Offen:** `_idealwine_reference` liest nach
der §4.2/4.3-Integration die vom Produzenten-/Wein-Matcher umgeschriebenen
`lots.wine`-Werte, nicht mehr zwingend die rohe idealwine-Schreibweise — zu
klären, ob das noch der gewünschten „iDealwine hat saubere, getrennte Felder"-
Begründung entspricht oder die Referenzliste hier Vorrang vor idealwine
bekommen soll.

**Format + Pflege:** versionierte CSVs im `data/reference/`, Spalten
`canonical, alias, …, reason`; jede Zeile mit Herkunftsgrund (wie bei den
bestehenden Overrides). Pflege via Review-Queue (§4.5).

## 4. Normalisierung (Match-Verfahren + Edge Cases)

**Prinzip (hart):** Der Build ist **deterministisch und ruft nie eine LLM-API**.
LLM-Ergebnisse existieren nur als **eingefrorene, reviewbare CSV-Artefakte**, die
an ihren Input gebunden sind (`wine_llm_overrides.csv`). So ist jeder Build
reproduzierbar und auditierbar. (Das ist der dokumentierte Vertrag in
`llm_review_producer.py`: *„This tool is OFFLINE and is never part of the
build."*) → **Damit ist `wine-lot-normalization-llm.md` obsolet.**

**Kosten-Denominator korrigieren (wichtig für dein Mehrstufen-Argument):** Die
LLM-Last sind **nicht 2,77 Mio Lots**, sondern **distinkte normalisierte
Aliasse**. Beleg-Query (bei gemounteter DB):

```sql
SELECT COUNT(DISTINCT alias_key) AS distinct_aliases FROM wine_alias_observations;
-- Erwartung: Grössenordnung ~wines (≈238k), also ~10× kleiner als 2,77 Mio.
```

Erst damit wird „mehrstufiges Matching zur Kostenoptimierung" konkret: lokal
löst die grosse Masse, der LLM sieht nur den distinkten Rest (und davon nur den,
den die lokalen Stufen 1–3 nicht schaffen).

### 4.0 Eintrittsbedingung: Gold-Set (zuerst!)

Ohne handgelabelte Wahrheit lässt sich **keine** Aussage treffen, ob ein neuer
(Fuzzy-)Matcher verbessert oder still verschlechtert. Daher **vor** jeder
Änderung an §4:

- [ ] **Gold-Set** `data/tests/fixtures/gold_lots.csv`: 300–500 Lots,
      stratifiziert über Häuser, inkl. der im Schwester-Plan genannten Fälle
      (Petrus-Vertikale, Sassicaia, Bernhard Huber) und der Edge Cases unten.
      Felder: erwarteter (producer, wine, vintage, qty, dl, is_ohk).
- [ ] **Regressionstest** `data/tests/test_gold_set.py`: misst Precision/Recall
      je Stufe; CI-Gate gegen Verschlechterung.

### 4.1 Stufe 0 — AMBIGUOUS-Splitting (höchster Hebel, halb gebaut)

**Befund:** `resolve_group()` liefert `AMBIGUOUS`, sobald eine `alias_key`-Gruppe
> 1 distinkten `producer_key` hat → es entsteht **kein** `wines`-Eintrag,
`_backfill_wine_ref` findet nichts (Lookup nur auf `alias_key`), die Lots
bekommen `wine_ref_id = NULL` und **verschwinden still** aus `single_wine_prices`.
Das ist **Produkt-Datenverlust**, nicht nur ein Flag.

**Das Schema kann es bereits:** `wine_alias_resolutions` ist
`UNIQUE(scope_key, alias_key, discriminator_key)` und `discriminator()` liefert
`producer_key`. Der Code *gibt nur auf*, statt zu splitten.

- [ ] **Vorab quantifizieren:** wie viele Lots hängen hinter AMBIGUOUS?
  ```sql
  SELECT COUNT(*) FROM lots
  WHERE lot_kind='SINGLE' AND wine_ref_id IS NULL;
  ```
- [ ] Für `conflicting-producer`-Gruppen **je `(alias_key, producer_key)` eine
      `wines`-Zeile** erzeugen (statt keiner); `_backfill_wine_ref` auf das Paar
      `(alias_key, producer_key)` umstellen. Nur echt unauflösbare Fälle (kein
      Produzent, widersprüchliche Evidenz) bleiben AMBIGUOUS.

### 4.2 Stufe 1 — Produzenten-Index (die „DAG"-Idee, konkret)

Dein DAG-Vorschlag ist präzise ein **invertierter Token-Index mit
Mengen-Schnitt**, nach Token-Abdeckung gerankt — bei dieser Grösse billig und
deterministisch:

- Aus `producers.csv` (§3) einen Index `token → {producer_id}` bauen.
- Für einen Alias: Tokens schneiden → Kandidaten-Produzenten, Rang nach Anteil
  abgedeckter Produzenten-Tokens („bernhard" ∧ „huber" ⇒ „Weingut Bernhard
  Huber"). Eindeutiger Treffer ⇒ Produzent abtrennen, Rest = Wein-Name.

### 4.3 Stufe 2 — Wein-Fuzzy-Match (produzenten-skopiert)

Erst **nach** erkanntem Produzenten gegen **dessen** Weinliste fuzzy matchen
(`rapidfuzz.token_set_ratio`, Schwelle auf dem Gold-Set kalibrieren). Das hält
den Vergleichsraum winzig und macht „R Schlossberg" → „Hecklinger Schlossberg",
„Malterdinger Pinot Noir" → „Malterdinger Spätburgunder", „Follin-Arbel" →
„Follin-Arbelet" lösbar — ohne globalen O(n²)-Fuzzy-Scan. `rapidfuzz` als neue
Abhängigkeit in `data/requirements.txt`.

### 4.4 Stufe 3 — LLM-Residuum (DeepSeek, offline, eingefroren)

Nur was Stufe 0–2 nicht auflösen, geht an den LLM — **generalisiertes Muster aus
`llm_review_producer.py`** (deepseek-flash, batched, `--workers`, `.state`-Resume,
`temperature=0`, JSON-`response_format`, 429-Retry, inkrementelles Schreiben).
Output = Override-CSV mit `reason=llm-review` + `confidence`; unsicher →
`*_rest.csv` in die Review-Queue. Build liest nur die CSVs.

### 4.5 Review-Queue (menschliche Kuratierung)

`wine_llm_rest.csv` + AMBIGUOUS-Reste + MISSING-Vintage
(`vintage_review_missing.csv`) sind bereits da. Ergänzen: einfacher Workflow, der
eine bestätigte Review-Zeile als Override mit `review_status='CURATED'`
zurückschreibt (höchste Vertrauensstufe, nie vom Auto-Resolver überschrieben).

### Edge Cases (explizit zu behandeln / im Gold-Set abgedeckt)

- **Vertikalen / Mixed-Lots** („Petrus vertical 1980–2016", „1989 1996 mixed"):
  → `vintage_status=MV`/`AMBIGUOUS`, `lot_kind=MIXED`, kein `price_per_bottle`
  (Logik vorhanden). Gold-Set prüft, dass sie **nicht** fälschlich SINGLE werden.
- **`(2 BT)`/`(6 BT)`** = Anzahl → `quantity`; Gebinde → `bottle_size_dl`
  (`bottle.py` vorhanden).
- **OHK/CBO/OWC** im Text → `is_ohk=true` (**neu**, §5). Aus Staging-Files kommt
  `isOHK` direkt als Spalte.
- **Abgeschnittene/Typo-Namen** → Stufe 2 (produzenten-skopierter Fuzzy).
- **Fehlender Jahrgang**: kein gültiger Single-Wein ohne Jahrgang
  (`single_wine_prices` filtert auf `STRUCTURED`/`EXTRACTED`).

## 5. Speicherung (Zielstruktur-Mapping statt Neubau)

Der Rumpf überzeichnet die Lücke. **Mapping VinoDomain → vorhandene Spalte →
Aktion:**

| VinoDomain | Python-Spalte heute | Aktion |
|---|---|---|
| `Wine.name` | `wines.canonical_name` / `lots.wine` | — vorhanden |
| `Wine.producer` | `wines.producer`, `lots.producer` | — vorhanden |
| `Wine.region` | `wines.region`, `lots.region` | — vorhanden |
| `Wine.origin` (Enum-Klassif.) | `lots.classification` | — vorhanden (nicht `origin_id`!) |
| Geografie (separat) | `lots.origin_id` → `wine_origins` | — vorhanden |
| `Wine.vintage` | `lots.vintage_final` | — vorhanden |
| `Unit.deciliters` | `lots.bottle_size_dl` | — vorhanden |
| `Offering.noOfBottles` | `lots.quantity` | — vorhanden |
| `Offering.providerOfferingId` | `lots.lot_no` | — vorhanden |
| `priceMin`/`priceMax` | `lots.estimate_low`/`estimate_high` | — vorhanden |
| `realizedPrice` | `lots.hammer_price` / `realised_price` | — vorhanden |
| `Offering.isOHK` | — | **❌ neu: `lots.is_ohk INTEGER`** |
| `Offering.note` | `lots.description` (nicht dasselbe) | **❌ neu: `lots.note TEXT`** |
| abgeleitet | — | **❌ neu: `lots.price_per_bottle REAL`** = `total_price/quantity`, **nur** SINGLE + 1 Jahrgang |
| `Rating`/`RatingAgency` | — | **❌ Gap** — offene Entscheidung (eigenes Teilprojekt) |

⇒ Echte Schema-Arbeit = **drei Spalten** (`is_ohk`, `note`, `price_per_bottle`)
plus Loader-Anbindung (`isOHK`/`note` aus den Staging-Files). CHECK-Constraint
für `price_per_bottle` (nur gesetzt wenn `lot_kind='SINGLE'` und ein Jahrgang).

## 6. FX-Problem

- [ ] Volle FX-Historie (Issue #97) — Zielwährung EUR, historische Kurse
  (AUD/USD/GBP/CHF/HKD/SGD/CNY → EUR) **zum `lot_date`**, Kurs + Kursdatum
  speichern. Heute ist `fx_rate` nur für NLG→EUR gefüllt. Eigenes Teilprojekt.
  **Quelle: ECB (EZB) Referenzkurse** (kostenlos, täglich, ab ~1999; SGD/HKD/CNY
  teils nicht abgedeckt — dann Rohwährung + Label). Bis dahin zeigt das MVP
  Rohwährung + `currency`-Label (siehe MVP-Plan §6).

## 7. Search Capabilities

- [ ] **FTS5**-Index über `canonical_name`/`producer`/`region` (contentless,
  aus `wines`). MVP nutzt noch `LIKE` (238k Namen, ausreichend).
- [ ] Autocomplete + Ranking (Präfix > Substring > Lot-Anzahl, wie im MVP-Plan).
- [ ] Facetten (Produzent, Region, Jahrgang, Gebinde, `is_ohk`).

## 8. GUI / UX

- [ ] Chart: X-Achse `lot_date` (dd.MM.yyyy) + Auktions-Location; FX-normalisiert
  (sobald §6 steht). Vor §6: Rohwährung + Label.
- [ ] Ergebnisliste (Produzent · Wein · Jahrgang · Gebinde · Anzahl · OHK).
- [ ] `price_per_bottle` anzeigen (nur wo sinnvoll, s. §5).

---

## Review-Befunde (Bugs/Risiken im Ist-Stand, in v2 mitzunehmen)

1. **AMBIGUOUS = stiller Datenverlust** (§4.1) — Lots verschwinden aus dem
   Produkt. Höchster Hebel.
2. ~~**`canonical_source`-Provenienz-Bug**~~ → **gefixt** (s. Kapitel 4.2–4.3
   im Progress-Log): `canonical_source`/`resolution_method` beschreiben jetzt
   dieselbe, einmal getroffene Namensentscheidung statt sie unabhängig und
   inkonsistent neu zu berechnen.
3. **iDealwine als stille Autorität** (§3) — als Policy dokumentieren, nicht
   implizit im Code lassen.
4. **Staging-Import unterschätzt** (§2) — Multi-Event/Multi-Schema-Workbooks.

## Offene Entscheidungen (noch zu klären)

- Referenzlisten-Pflegeprozess (CSV + Review-Queue-Rückschreibung).
- Fuzzy-Schwellen (auf dem Gold-Set zu kalibrieren) — inkl. des
  Single-Token-Kollisionsrisikos aus §4.2 (s. Progress-Eintrag): ggf.
  `PRODUCER_COVERAGE` pro Produzent anheben, wenn dessen kanonischer Name nach
  Stopword-Filterung nur 1 Token hat, oder gegen eine Appellations-/Region-
  Liste abgleichen, bevor ein Single-Token-Treffer akzeptiert wird.
- ~~FX-Quelle~~ → **ECB (EZB) Referenzkurse** (entschieden).
- ~~Ratings~~ → **nein, nicht fürs MVP** (separates Issue).
- Zukunft von `VinoDomain`/`VinoImporter`: Referenz-/Legacy-Parser behalten
  (PDF-Häuser) oder vollständig in Python ablösen?

## Progress

- [x] Kapitel 2: Prüfschritt + Rebuild gegen Master-DB erledigt.
  `load_steinfels_staging` + `load_wermuth_validated` eingebunden; der im
  Rumpf geforderte Dubletten-Check gegen `load_wermuth` fehlte zunächst und
  wurde nachträglich an der echten DB verifiziert + gefixt (4 echte
  Terminüberschneidungen + 2 openpyxl-Artefakte — Details + finale Zahlen
  in Kapitel 2 oben). `is_ohk` befüllt. Backups: `.bak-historic`,
  `.bak-pre-wermuth-fix`.
- [ ] Kapitel 3: Referenzlisten (producers.csv, units.csv, ohk.csv; idealwine-Policy)
- [x] Kapitel 4.0 (Gerüst): `build_gold_set.py` + `gold_lots.csv` (495 Kandidaten,
  stratifiziert, inkl. Edge-Case-Queries) + `test_gold_set.py` (Regressionstest,
  schlägt fehl bis ≥50 gelabelt). Offen: **Labeling der expected-Spalten** (manuell).
- [x] Kapitel 4.1: AMBIGUOUS-Splitting — Rebuild: **AMBIGUOUS 12 → 0**,
  wines 238.987 → 239.607 (+620), unresolved SINGLE 8.726 → 8.689. Backup
  `.bak-ambiguous`.
- [x] Gebinde-Extraktion: `bottle.py` erweitert (parst `description` zusätzlich,
  Liter-Formate `0,75l`/`6l`, `Flasche`/`Magn`) → Gold-Set-Accuracy
  **16,18 % → 86,13 %**. Tests 103 grün.
- [x] Kapitel 4.2–4.3: Produzenten-Index (`producer_match.py`, invertierter
  Token-Index über `producers.csv`) + produzenten-skopierter Fuzzy-Match
  (`rapidfuzz.token_set_ratio` über `wines_by_producer.csv`) in
  `_build_observations` integriert. `rapidfuzz` zu `requirements.txt`
  ergänzt (offene Abhängigkeit aus §4.3). 5 Tests grün
  (`test_producer_match.py`), 109 Tests gesamt grün.
  **Senior-Review (zweite Runde, mit Advisor) — vier echte Bugs gefunden und
  gefixt, nicht nur der Tippfehler, an dem DeepSeek hängen blieb:**
  1. **`match_producer`-Ranking war strukturell falsch, nicht nur ein
     Tiebreak-Detail.** Coverage wurde gegen die Token-Zahl des *kanonischen
     Namens* berechnet, auch wenn der Treffer über einen ganz anderen,
     längeren Alias kam — z. B. matchte „Moët Chandon" fälschlich „Dom
     Pérignon", weil dessen Alias „Moët & Chandon Dom Pérignon" 3 Treffer
     lieferte, geteilt durch die 1-Token-Länge des kanonischen Namens „Dom
     Pérignon" (coverage 3/1 > 1.0) — höher als „Moët & Chandon"s eigene
     coverage 2/2. **Fix:** Coverage wird jetzt pro Alias berechnet
     (Treffer / Tokens *dieses* Alias, nicht des kanonischen Namens), pro
     Produzent wird nur der beste Alias gewertet. Ein echter Tie nach
     (Coverage, Treffer) gibt `None` zurück statt zufällig zu wählen (§4.2:
     „Eindeutiger Treffer ⇒ Produzent abtrennen"). Verifiziert: alle 1008
     Alias/Canonical-Paare aus `producers.csv` matchen sich selbst
     (4 erwartete Ausnahmen, s. u.), stabil über 4 verschiedene
     `PYTHONHASHSEED`-Werte (vorher: hash-abhängig, nicht reproduzierbar).
  2. **`lots.wine_ref_id` blieb für JEDEN per Matcher normalisierten Lot
     NULL — stiller Datenverlust, exakt die Kategorie, die §4.1 beheben
     sollte.** `_build_observations` hat `wine`/`producer` nur in einer
     lokalen Variable umgeschrieben, nie in `lots` zurückgeschrieben.
     `_backfill_wine_ref` las weiterhin die unveränderte `lots.wine`-Spalte
     und fand dadurch nie den (neuen, umgeschriebenen) `alias_key`, unter
     dem `wine_alias_resolutions` den Treffer tatsächlich abgelegt hatte.
     Fixture-Beweis vor dem Fix: alle 6 Test-Lots hatten `wine_ref_id IS
     NULL`, trotz korrekt aufgelöster `wines`/`wine_alias_resolutions`.
     **Fix:** `_build_observations` schreibt die gematchten Werte zurück
     (`UPDATE lots SET wine=?, producer=?`), analog zu `_separate_vintage`,
     das das schon für `wine` macht. **Neuer Regressionstest**
     `test_single_lots_backfilled` (`test_repeatability.py`): 0 SINGLE-Lots
     ohne `wine_ref_id` — das hätte den Bug gefangen, vorher gab es keine
     Prüfung dafür.
  3. **`canonical_source`-Provenienz-Bug (Review-Befunde #2) gefixt** — nicht
     durch Vorrang-Umkehr (idealwine vs. Override), sondern durch
     Angleichung des Labels an die tatsächlich verwendete Quelle:
     `resolve_group` bekommt jetzt `forced or idealwine_name` (Override
     schlägt idealwine — konsistent mit §4.5 „CURATED = höchste
     Vertrauensstufe"), `canonical_name = res["canonical_name"]` direkt
     (keine zweite, abweichende `forced or ...`-Rekonstruktion mehr), und
     `canonical_source`/`resolution_method` beschreiben beide dieselbe,
     einmal getroffene Entscheidung (`source`-Variable) statt sie
     unabhängig und inkonsistent neu zu berechnen.
  4. **`wine_resolution/spirits.py` existierte, war aber nirgends
     eingebunden** — Spirituosen-Lots (Armagnac, Cognac, …) liefen
     unverändert durch die Wein-Auflösung und bekamen falsche
     Produzenten/Weine zugewiesen (Gold-Set-Beleg: „Marquis de Montdidier
     Armagnac" bekam einen Produzenten aus Wortüberlappung zugewiesen,
     erwartet war `NON_WINE`). **Fix:** `_classify_lots` ruft jetzt zuerst
     `_exclude_spirits` auf, markiert Treffer als `lot_kind='UNKNOWN'`
     (`mixed_reason='spirit'`), bevor die generische Klassifikation läuft.
  **Kalibrierung gegen echte Daten statt nur synthetischer Beispiele:**
  `match_producer`/`match_wine` über alle 495 Zeilen aus
  `tests/fixtures/gold_lots.csv` laufen lassen (405 mit echtem Produzenten,
  MIXED/NON_WINE ausgeschlossen) → **375 richtig, 29 konservativ kein
  Treffer, 2 falsch-positiv** (1,5 % → nach Wiederherstellung generischer
  Stopwords 0,5 %; s. u.). Das validierte zugleich die ursprünglich zu
  aggressiv wirkenden Stopwords (de/du/la/le/les/et/grand/vin/clos/vieux/
  cru/gcc/premier/1er): mit dem korrekten Alias-Coverage-Ranking (Fund 1)
  sind sie kein Risiko mehr, sondern senken die Falsch-Positiv-Rate
  nachweisbar (6/406 → 2/406 auf dem Gold-Set) ohne neue Regressionen.
  **Rebuild gegen Master-DB nachgeholt** (Samsung war zwischenzeitlich
  gemountet) — 0 AMBIGUOUS (unverändert ggü. Kapitel 4.1), unresolved SINGLE
  8.690 (Kapitel 4.1: 8.689 — stabil, keine Regression). Details zum Rebuild
  selbst (inkl. des dabei gefundenen Wermuth-Dubletten-Bugs) s. Kapitel 2.
  **Restrisiko (nicht blind fixen, siehe „Offene Entscheidungen"):** die 2
  verbleibenden Gold-Set-Falsch-Positive sind beide Appellations-/
  Klassifikations-Text ohne echten Produzentenbezug, der zufällig ein
  Produzenten-Token trifft — „GCC2 Margaux" (Appellation „Margaux") →
  „Château Margaux"; „Châteauneuf du Pape «Cuvée Laurence»" → „Château Pape
  Clément" (statt „Domaine du Pégau"). 177 von 556 Produzenten (~32 %)
  reduzieren sich nach Stopword-Filterung auf einen einzigen Token — eine
  weitere Stopword-Runde ist Raten ohne Gold-Set-Beleg; eine robustere
  Lösung wäre, Single-Token-Kandidaten gegen die vorhandene
  Appellations-Referenz (`wine_origin_reference_multilingual.csv`) zu
  prüfen, bevor sie akzeptiert werden. **Separat zu entscheiden:**
  `_idealwine_reference` läuft nach `_build_observations` und liest damit
  jetzt die vom Matcher umgeschriebenen `lots.wine`-Werte statt der
  rohen idealwine-Schreibweise — ein Referenzlisten-Treffer kann die
  idealwine-Schreibweise dadurch für andere Häuser überschreiben, bevor
  idealwine selbst als Autorität greift. Das ist mit der doku­mentierten
  idealwine-Policy (§3) abzustimmen, nicht nebenbei zu fixen.
- [ ] Kapitel 4.4: LLM-Residuum-Stufe (DeepSeek, eingefroren)
- [x] Kapitel 5 (teils): Schema `is_ohk`, `note`, `price_per_bottle` + `_to_bool`;
  Loader-Anbindung in load_wermuth/load_steinfels_staging. Offen:
  price_per_bottle-Ableitung + CHECK-Constraint.
- [ ] Kapitel 6: FX (separates Issue #97)
- [ ] Kapitel 7: Search (FTS5)
- [ ] Kapitel 8: GUI/UX
- [x] Bug: canonical_source-Provenienz (gefixt im Zuge von Kapitel 4.2–4.3,
  s. o.)
