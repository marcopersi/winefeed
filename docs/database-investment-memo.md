# Investitions-Dokumentation — Beleg für sui-generis-Datenbankschutz (6.1.1)

> **Zweck:** Beleg der "wesentlichen Investition" in Beschaffung, Überprüfung,
> Bereinigung und Darstellung der Auktionspreis-Datenbank — Tatbestandsmerkmal
> des EU-Datenbankherstellerrechts (sui generis, Richtlinie 96/9/EG Art. 7).
> **Korrektur, Copilot-Review 2026-11-15:** die Schweiz kennt KEIN
> eigenständiges sui-generis-Datenbankherstellerrecht (Richtlinie 96/9/EG
> nie übernommen) — eine frühere Fassung dieses Dokuments behauptete das
> fälschlich ("EU/CH"-Recht). Für die Schweiz ist dieses Memo allenfalls
> Beleg für Urheberrechtsschutz (Art. 4 URG, falls die Datenbank eigene
> Originalität in Auswahl/Anordnung aufweist) und für das UWG; für das
> EU-Recht gilt zudem die Berechtigten-Voraussetzung nach Art. 11 der
> Richtlinie (Sitz/Staatsangehörigkeit des Betreibers in der EU/EWR, nicht
> die Existenz von EU-Nutzern) — von 6.1.4 zu prüfen, s.
> `docs/tos-anti-scraping-clause.md` Ziffer 6(2). Referenziert von
> `docs/tos-anti-scraping-clause.md` Ziffer 6(1) und von
> `docs/data-api-security-plan.md` Schritt 6.1.1. Arbeitsgrundlage für die
> Rechtsberatung (6.1.4), keine rechtliche Bewertung. Stand: 2026-11-15.

## 1. Umfang der Datenbank (verifiziert 2026-11-14/-15, s. Zeilen unten)

| Kennzahl | Wert |
|---|---|
| Auktionshäuser/Provider | 24 |
| Auktionen | 9'078 |
| Rohdaten-Lose | 4'297'347 |
| Bereinigte, aufgelöste Einzelwein-Lose (`single_wine_prices` — `lot_kind='SINGLE'`, Wein-Referenz aufgelöst, Jahrgang sauber; **nicht** bereits prognosefähig, s. Korrektur unten) | 3'232'827 |
| Davon tatsächlich prognosefähig, **Momentaufnahme 2026-11-15** (`forecast_input` — zusätzlich `sold=1`, `lot_date`/Preis vorhanden, `price_kind IS NULL` [schliesst idealwines COTE-Bewertungen aus, auch wenn Preis/Datum vorhanden sind], kein OUTLIER/QTY_SUSPECT/DUP_CANDIDATE, UND `series_last_obs >= date('now','-36 months')` — diese letzte Bedingung ist **zeitabhängig**, die Zahl verschiebt sich bei jeder Neuberechnung mit dem Kalenderdatum, keine stabile DB-Eigenschaft, s. `data/build_db.py` Zeilen 384–413) | 970'984 |
| Aufgelöste, eindeutige Wein-Referenzen | 269'884 |
| Zeitliche Abdeckung | 1998-01-31 – 2026-11-20 (28 Jahre) |
| Datenbankgrösse (SQLite, Samsung-Disk) | 3.47 GB |

## 2. Umfang der Beschaffungs-/Aufbereitungs-Pipeline (verifiziert gegen das Repo)

| Kennzahl | Wert |
|---|---|
| Eigene Fetcher-Module | 22 Python-Module (`ingest/fetchers/*.py`), bedienen 23 der 24 Provider -- **Korrektur, Copilot-Review 2026-11-15 (2 Runden):** "ein Modul pro Haus" war ungenau (`WeinauktionFetcher` bedient steinfels UND weinboerse gemeinsam); idealwine/christies sind bereits in diesen 22 Modulen enthalten, nicht zusätzlich dazu -- ihr Delta- bzw. Backfill-Mechanismus liegt aber NICHT im Fetcher-Modul selbst, sondern in eigenen Orchestrierungs-Skripten (`data/run_idealwine_delta.py`, `data/run_christies_backfill.py`), die das jeweilige Fetcher-Modul aufrufen. Registry-Key ≠ DB-Provider-Name: der Fetcher-Modul-Key `denzauktionen` schreibt in den DB-Provider `wermuth-sa` (Nachfolger des Wermuth/Denz-PDF-Archivs, s. `data/orchestrate.py` Zeilen 40–45) -- `wermuth-sa` ist entgegen einer früheren Fassung dieser Zeile also NICHT unversorgt. Nur `zacky` hat wirklich kein Fetcher-Modul (eigener statischer `load_zacky`-Loader in `data/build_db.py`, kein `ingest/fetchers/`-Eintrag). |
| Code-Umfang Fetcher allein | 3'848 Zeilen |
| Code-Umfang Build-/Ingest-Orchestrierung (`data/build_db.py`, `data/run_ingest.py`) | 5'473 Zeilen |
| Entwicklungszeitraum (erster Ingest-Commit → heute) | 2026-09-24 – 2026-11-14 (51 Tage durchgehend) |
| Commits allein an Ingest/Build-Pipeline | 105 |
| Automatisierung | monatlicher CI-Cron (`.github/workflows/ingest.yml`) + separater CI-Schritt für idealwine; Sothebys/weitere Häuser laufen aus technischen Gründen lokal |

## 3. Qualitativer Beleg: die Daten sind nicht trivial beschaffbar

Mehrere Häuser erforderten gezielte, hauseigene Gegenmassnahmen gegen
Bot-Abwehr — das ist selbst ein Beleg dafür, dass die Datenbasis nicht durch
einen trivialen `requests.get`-Scraper reproduzierbar ist, sondern das
Ergebnis gezielter technischer Investition:

- **Sothebys:** camoufox-Browser-Automation + Residential-IP-Pool + gelöstes
  Cloudflare-Turnstile (dokumentiert in `AGENTS.md`, läuft bewusst nur lokal).
- **idealwine:** eigener zeitstempel-basierter Checkpoint-Mechanismus statt
  ID-basierter Dedup, weil sich Cote-Seiten über Zeit inhaltlich ändern.
- Weitere Häuser mit individueller Fetcher-Logik je nach Seitenstruktur
  (22 eigenständige Module, kein generischer Scraper).

## 4. Noch zu ergänzen (nicht aus dem Repo ableitbar)

- [ ] **Tatsächlicher Stundenaufwand** (eigene Zeit, ggf. auch Zeit Dritter)
      — die 105 Commits/51 Tage sind ein Indiz, aber kein Stundennachweis.
- [ ] **Direkte Kosten** (z. B. Residential-IP-/Proxy-Dienste, Compute,
      Cloud-Hosting-Kosten für Entwicklung/CI), soweit bezifferbar.
- [ ] Ggf. **Lizenz-/Datenbezugskosten**, falls für einzelne Häuser
      kostenpflichtige Zugänge genutzt wurden.

> Diese drei Punkte sind der Rechtsberatung (6.1.4) zur Vervollständigung zu
> übergeben — sie stärken den Investitionsnachweis, sind aber für die
> Existenz des Schutzrechts nicht zwingend erforderlich (die oben
> verifizierten Umfangs- und Komplexitätskennzahlen allein sind bereits ein
> starkes Indiz für eine "wesentliche Investition").
