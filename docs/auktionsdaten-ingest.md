# Bauplan: Periodischer Auktionsdaten-Ingest (CI-scheduled)

Status: `PLANNING` — wartet auf Freigabe und auf offene Entscheidungen (§3.4).

---

## 1. Summary

- **Ziel:** Auktionsdaten aller Häuser **1×/Monat** automatisch beziehen
  (Scraping/API + PDF-Download gemischt), Rohdaten in einen Cloud-Artifact-Store
  speichern und die bestehende Verarbeitung deterministisch anstoßen — als
  scheduled GitHub-Actions-Job.
- **Betroffene Subsysteme:** `data/` (aktive Python-Pipeline), neues Modul
  `ingest/`, GitHub-Actions-Workflows (`.github/workflows/`), optional
  `VinoImporter` (nur bei PDF-Weg A).
- **Hauptrisiko:** Die Quellenliste (URLs/Endpoints/Selektoren) liegt außerhalb
  dieser Session und ist Voraussetzung für die Fetcher-Implementierung.
- **Betroffen:** Workflow (Scheduling/Trigger-Kette), Security (Secrets).
  Keine zwingende Schema-Änderung an `build_db.py` (nutzt bestehende
  `UNIQUE(provider_id, auction_id)`-Constraints).

## 2. Established facts

Nur durch Codebeleg gestützt:

- `data/build_db.py` baut `wine_auction_prices.sqlite` deterministisch; liest
  „14 JSON-Häuser“ plus Wermuth/Steinfels CSV/Excel; Schema mit
  `UNIQUE(provider_id, auction_id)`; `DB_PATH` default
  `/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite`, `ARCHIVE_PATH`
  default `~/Library/CloudStorage/GoogleDrive-persi.marco@gmail.com/Meine Ablage/Wein/WeinAuktionspreise`
  (`data/build_db.py:23-34`).
- `data/materialize.py` materialisiert Google-Drive-JSONs lokal
  (`data/materialize.py:13-15`).
- `data/normalize_idealwine.py` normalisiert iDealwine-JSONs
  (`data/normalize_idealwine.py:23-28`).
- `data/build_wines.py` macht Wine-Resolution; `data/generate_review_csv.py`
  erzeugt Review-CSV (`data/generate_review_csv.py:14`).
- `VinoImporter` ist dateibasiert: PDFs in `import/<Provider>/`, Starter per
  Hand (`SteinfelsStarter`/`WermuthStarter`/`WeinboerseStarter`), Verzeichnisse
  in `VinoImporter/resources/config.xml` und `SteinfelsImportTask`
  (`@Value("import//Steinfels//")`).
- Bestehender CI-Workflow `.github/workflows/ci.yml` nutzt Python 3.12,
  `pip install -r data/requirements.txt`, `python -m unittest discover -s data/tests`
  und `./gradlew build`.
- Kein automatisierter Fetch vorhanden; Quellenliste je Haus in §2b
  (rekonstruiert aus Session-Historie, nicht vollständig im Repo).
- User-Entscheidungen dieser Session: (1) Fetch = Scraping/API + PDF-Download
  gemischt; (2) Laufzeit = GitHub Actions `schedule` (cron); (3) Ablage =
  Git-Repo/Artifact-Store.

## 2b. Quellenliste je Haus (rekonstruiert aus Session-Historie)

Stand der Nachvollziehbarkeit: Die **Fetch-Skripte** der meisten Häuser lagen im
temporären Arbeitsverzeichnis (`/var/folders/…/opencode/`) und wurden beim
Aufräumen entfernt. Erhalten bzw. rekonstruiert sind: die **curl-Skripte auf der
externen Disk** (Steinfels, Weinboerse, Munich Wine Company, Koppe — enthalten
die exakten Request-URLs), die **iDealwine-/sylvies-Endpoints im Repo** und die
**Quell-URLs in den gespeicherten JSONs** (`source_url`/`snapshot_url`/
`landing_url`/`results_pdf`). Für die restlichen Häuser (Sotheby's, HDH,
Langtons, Winefields, Besch Cannes, Dorotheum, Pandolfini, Dobiaschofsky,
Finarte, winebarrel, weinauktionator) fehlen die exakten Endpoints noch.

| Haus | Quelle | Methode | Bekannte URLs/Endpoints |
|------|--------|---------|-------------------------|
| iDealwine | idealwine.com | öffentl. JSON-API (kein Login) | `/api/v2/shop/vintage-ratings-by-product-for-region-d-t-os/by-region/{region}` (Enumeration, paginiert); `/api/v2/shop/product-vintage-rating-info/{pid}-{vintage}` (Preis-Historie). Regionen: `bordeaux`, `bourgogne`, `rhone` |
| sylvies | sylvies.be | HTML-Scrape | `/en/auction/{id}?sort=lotnr_asc&page={n}` |
| Sothebys | sothebys.com | API | JSON mit `auction_id` (UUID), `sale_number`, `hammer_price` + `final_price` |
| Christies | christies.com | Scrape | Auktions-`landing_url`: `https://www.christies.com/en/auction/{slug}-{saleId}/`; Lot-URL: `https://www.christies.com/en/lot/lot-{lotId}` |
| Zacky | auction.zachys.com via **Wayback** | Wayback-Snapshot | `https://auction.zachys.com/catalog.aspx?auctionid={id}`; nur Seite 1 (25 Lots) archiviert, Postback-Paginierung fehlt |
| Baghera | bagherawines.auction | Scrape | `results_pdf`: `https://www.bagherawines.auction/assets/uploads/bilan/catalogues/{id}/…_Sale_Results.pdf` |
| HDH | hdhwine.com | Scrape | `hammer` + `aggregate` |
| Langtons | langtons.com.au | API | `winning_bid` (AUD) |
| Winefields | winefields.com | API (Auction-Mobility) | `hammer` |
| Besch Cannes | besch-cannes.com | Scrape | `adjuge` |
| Munich Wine Company | munichwinecompany.com | HTML-Scrape | `https://www.munichwinecompany.com/de/{id}/live-wineauction-p{i}.html` (Seiten-Pagination `p{i}`) |
| Dorotheum | dorotheum.com | API | `realized_price` |
| Pandolfini | pandolfini.it | Scrape | `sold_price` (inkl. Aufgeld) |
| Dobiaschofsky | dobiashofsky.ch | Scrape | `hammer_chf` |
| Finarte | finarte.it | Scrape | `hammer_price` |
| winebarrel | (unbekannt, flache Lot-Liste) | Scrape | `hammer_price` |
| weinauktionator | weinauktionator (?) | XLSX/PDF | — |
| Wermuth | Excel bereitgestellt/extrahiert | via `VinoImporter` | `VinoImporter/validatedOutput/vinoStagingFile2015-2008.xlsx` + `output_WermuthSA_*.csv` |
| Steinfels | auktionen.steinfelsweine.ch | JSON-API | Auktionsliste `…/api/auctions` (→ `catalog.id`); Lots `…/api/lots?cat_id={catalogId}&my=false&s=&consignments_only=false&$sortby=lot_number&$sortdir=asc&$page={i}&$maxpagesize=50`; Header `x-api-version: 1.14`. Alt-Bestand (2002–03) als Excel `priceData/import/steinfels/prepared/*/results_*.xlsx` |
| Denz | denz.ch | PDF (noch nicht extrahiert) | — |
| FranzWermuth | wermuth.ch | PDF | — |
| Koppe | weinauktion.de | HTML-Scrape | `https://www.weinauktion.de/index.php?site=auktion&section=cat&cat={catId}&p={i}` |
| Weinboerse | auktion.weinauktion.ch | JSON-API | `https://auktion.weinauktion.ch/api/lots?cat_id={catalogId}&…&$page={i}&$maxpagesize=20` (gleiche API-Struktur wie Steinfels) |

## 3. Scope

### 3.1 In Scope

- Neues Python-Modul `ingest/` mit Fetcher-Interface, Registry/Dedup und
  einem Fetcher je Haus (Web/API und PDF).
- Cloud-Ablage der Rohdaten (GitHub Releases in einem Daten-Repo) und ein
  versioniertes Zustands-Manifest.
- Zwei Workflows: `ingest` (cron + `workflow_dispatch`) und `process`
  (Trigger-Kette materialize → normalize → build_db → build_wines → review).
- Secrets-Handling über GitHub-Secrets; Ergebnis-Zusammenfassung (Job-Summary).

### 3.2 Explizit Out of Scope

- Parser-Migration (Python vs. Java) — siehe offene Entscheidung §3.4.
- Echtzeit-/Inkrementelles Scraping, eigene Server-Infrastruktur.
- Umbau des `build_db.py`-Schemas oder der Wine-Resolution.
- Öffentliche Bereitstellung der Daten.

### 3.3 Bewiesene Annahmen

- Die Python-Pipeline (`data/`) ist die aktive, DB-erzeugende Pipeline.
- `build_db.py` ist deterministisch und über `UNIQUE`-Constraints idempotent —
  doppelt eingespielte Auktionen werden vom Schema abgefangen.
- GitHub Actions hat keinen Zugriff auf lokales Google Drive/`/Volumes/samsung`;
  `ARCHIVE_PATH`/`DB_PATH` sind bereits per Env überschreibbar.

### 3.4 Offene Entscheidungen (Freigabe erforderlich)

1. **Quellenliste:** Domains/Methoden je Haus sind rekonstruiert (§2b). Die
   genauen Fetch-Endpoints/Selektoren für die meisten Häuser fehlen noch (lagen
   in entfernten Fetch-Skripten) → für Step 4 je Haus neu zu ermitteln.
2. **PDF-Parsing:** Weg A (Java `VinoImporter` im CI → CSV) vs. Weg B
   (PDF-Parsing nach Python konsolidieren). → Blocker für Step 5.
3. **Daten-Repo:** neues privates `winefeed-data` vs. bestehendes Repo.
   → Blocker für Step 2.
4. **Review-Verteilung:** GitHub Issue/PR vs. nur CSV-Artifact. → Step 7.

## 4. Evolutionary micro-steps

### Step 1 — `ingest/`-Modulgerüst + Fetcher-Interface

- **Ziel:** Modul und gemeinsame Verträge schaffen, ohne Haus-Logik.
- **Dateien:** `ingest/__init__.py`, `ingest/fetcher.py` (Protokoll:
  `discover(seen) -> list[AuctionRef]`, `fetch(ref) -> Path`),
  `ingest/registry.py` (Manifest lesen/schreiben), `ingest/models.py`
  (`AuctionRef`).
- **Regel/Muster:** Python, PEP-8-konform wie `data/`; keine neue Dependency
  über `requests`/stdlib hinaus ohne Begründung; Logging wie bestehende Skripte
  (`print`/`flush` in `data/materialize.py` als Referenz).
- **Validierung:** `python -m unittest discover -s ingest/tests -v`;
  Manifest-Roundtrip-Test (leeres Manifest → Eintrag → laden).
- **Fertig wenn:** `ingest/` importierbar, Interface-Tests grün.
- **Abhängigkeiten:** keine.

### Step 2 — Cloud-Ablage + Manifest-Schema einrichten

- **Ziel:** Release-Mechanik und persistenter Zustand („gesehene“ Auktionen).
- **Dateien:** `ingest/storage.py` (Release-Assets hochladen via `gh`/API),
  `ingest/manifest.schema.json`, `state/manifest.json` (initial leer).
- **Regel/Muster:** Ablage-Entscheidung §3.4.3 beachten; Manifest
  `{provider: {auction_id: {url, etag, fetched_at}}}`; committet.
- **Validierung:** `ingest/storage.py` im Trockenmodus (kein echter Upload);
  Manifest-Schema gegen Beispieldaten validieren.
- **Fertig wenn:** Manifest lesbar/committierbar, Upload-Pfad getestet (Dry-run).
- **Abhängigkeiten:** Step 1; **Blocker:** Entscheidung §3.4.3.

### Step 3 — Registry/Dedup-Logik

- **Ziel:** `discover()` liefert nur neue Auktionen; idempotent.
- **Dateien:** `ingest/registry.py` (Dedup gegen Manifest + ETag).
- **Regel/Muster:** `UNIQUE(provider_id, auction_id)` in `build_db.py` als zweite
  Schutzschicht nutzen, nicht ersetzen.
- **Validierung:** Unit-Tests: bereits gesehene `auction_id` wird gefiltert;
  geänderte URL/ETag wird als Update erkannt.
- **Fertig wenn:** Dedup-Tests grün.
- **Abhängigkeiten:** Step 2.

### Step 4 — Fetcher je Haus implementieren

- **Ziel:** Pro Haus ein Fetcher (Web/API: JSON im bestehenden Format; PDF:
  PDF + `meta.json`).
- **Dateien:** `ingest/fetchers/<haus>.py` (iDealwine, sylvies, …),
  `ingest/fetchers/__init__.py` (Registry der Fetcher).
- **Regel/Muster:** JSON-Ausgabe kompatibel zu dem, was `build_db.py` bereits
  liest; PDF-Ausgabe nach `import/<Provider>/`-Konvention.
- **Validierung:** Je Fetcher ein Fixture-Test (gemockte HTTP-Antwort).
- **Fertig wenn:** Alle Häuser-Fetcher gegen Fixtures grün.
- **Abhängigkeiten:** Step 3; **Blocker:** Entscheidung §3.4.1 (Quellenliste).

### Step 5 — PDF-Haus-Adapter (Parsing-Weg)

- **Ziel:** Heruntergeladene PDFs in die von `build_db.py` erwarteten CSV/Excel
  überführen.
- **Dateien:** Weg A → CI ruft Java-Starter (`./gradlew :VinoImporter:…`),
  `ingest/pdf_pipeline.py`; Weg B → neuer Python-PDF-Parser.
- **Regel/Muster:** Ergebnis muss der bestehenden Wermuth/Steinfels-CSV-Struktur
  entsprechen (Referenz: `VinoImporter/validatedOutput/`).
- **Validierung:** Ein bekannter PDF-Datensatz → erwartete CSV-Zeilen;
  `./gradlew build` (Weg A) bzw. Parser-Unit-Test (Weg B).
- **Fertig wenn:** PDF → CSV deterministisch und build_db-kompatibel.
- **Abhängigkeiten:** Step 4; **Blocker:** Entscheidung §3.4.2.

### Step 6 — Workflow `ingest`

- **Ziel:** Monatlicher Fetch-Lauf, Release + Manifest-Commit bei neuen Daten.
- **Dateien:** `.github/workflows/ingest.yml`.
- **Regel/Muster:** `schedule` nur auf `master`; `on: schedule` + `workflow_dispatch`;
  `concurrency` wie `ci.yml`; Python-Setup wie `ci.yml` (3.12).
- **Validierung:** `act`-Trockenlauf oder `workflow_dispatch` im Repo.
- **Fertig wenn:** Lauf erzeugt Release nur bei neuen Daten; Manifest aktualisiert.
- **Abhängigkeiten:** Steps 2–5.

### Step 7 — Workflow `process` + Review-Verteilung

- **Ziel:** Verarbeitung nach Ingest anstoßen; Review-Output bereitstellen.
- **Dateien:** `.github/workflows/process.yml` (Trigger `repository_dispatch`
  oder `workflow_run`); Kette materialize → normalize → build_db → build_wines →
  generate_review_csv.
- **Regel/Muster:** Deterministisch; `DB_PATH`/`ARCHIVE_PATH` per Env auf
  Release-Assets; Review-Verteilung gemäß Entscheidung §3.4.4.
- **Validierung:** End-to-End auf einem Release-Snapshot.
- **Fertig wenn:** Kette läuft durch, Review-CSV liegt als Artifact (bzw. Issue/PR).
- **Abhängigkeiten:** Step 6; **Blocker:** Entscheidung §3.4.4.

### Step 8 — Secrets, Observability, Notifications

- **Ziel:** Credentials sicher, Lauf nachvollziehbar, Fehler sichtbar.
- **Dateien:** `ingest.yml`/`process.yml` (Secrets, Job-Summary),
  Notification-Hook.
- **Regel/Muster:** Secrets ausschließlich aus `${{ secrets.* }}`; kein Secret in
  Logs; Zusammenfassung „neu/übersprungen/fehlgeschlagen“ je Haus.
- **Validierung:** Fehlerlauf eines Fetchers bricht den Rest nicht; Notification
  feuert.
- **Fertig wenn:** Job-Summary + Fehlerpfad nachweisbar.
- **Abhängigkeiten:** Steps 6–7.

## 5. Validation matrix

| Betroffenes | Validierung |
|---|---|
| Python (Fetcher/Registry/Storage) | `python -m unittest discover -s ingest/tests -v` |
| Bestehende Pipeline nicht gebrochen | `python -m unittest discover -s data/tests -v` |
| DB-Reproduzierbarkeit | `python3 data/build_db.py --dry-run` |
| Java-PDF-Weg (falls A) | `./gradlew build` |
| Lint | bestehender super-linter in `.github/workflows/ci.yml` |
| Workflow-End-to-End | `act` bzw. `workflow_dispatch`-Testlauf |

## 6. Risks and rollback

- **Duplikate durch Dedup-Fehler:** durch Manifest + `UNIQUE`-Constraint
  abgefangen; Rollback = Manifest zurücksetzen und `build_db` neu laufen lassen.
- **Quellen-/API-Bruch (HTML/API ändert sich):** Fetcher schlägt isoliert fehl,
  Job wird rot, Notification feuert; kein Datenverlust (idempotent).
- **Kein Zugriff auf Google Drive/`/Volumes/samsung` in CI:** Ablage erfolgt über
  Release-Assets; `ARCHIVE_PATH`/`DB_PATH` per Env gesetzt.
- **Secret-Leak:** nur GitHub-Secrets; kein Loggen von Credentials.
- **60-Tage-Deaktivierung scheduled Workflows:** Manifest-Commit hält das Repo
  aktiv.
- **Partieller Lauf (ein Haus fehlt):** kein teilweiser „Erfolg“ melden —
  Job-Summary listet Fehlschläge explizit.

## 7. Approval gate

Freigabe erforderlich für den Gesamtscope (§3.1) und konkret für die offenen
Entscheidungen §3.4.1–§3.4.4. Erst danach Wechsel `PLANNING → IMPLEMENTING`.

---

## Progress

- [ ] Step 1: `ingest/`-Modulgerüst + Fetcher-Interface
- [ ] Step 2: Cloud-Ablage + Manifest-Schema (Blocker: §3.4.3)
- [ ] Step 3: Registry/Dedup-Logik
- [ ] Step 4: Fetcher je Haus (Blocker: §3.4.1)
- [ ] Step 5: PDF-Haus-Adapter (Blocker: §3.4.2)
- [ ] Step 6: Workflow `ingest`
- [ ] Step 7: Workflow `process` + Review-Verteilung (Blocker: §3.4.4)
- [ ] Step 8: Secrets, Observability, Notifications
