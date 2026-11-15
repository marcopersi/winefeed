# Investitions-Dokumentation — Beleg für sui-generis-Datenbankschutz (6.1.1)

> **Zweck:** Beleg der "wesentlichen Investition" in Beschaffung, Überprüfung,
> Bereinigung und Darstellung der Auktionspreis-Datenbank — Tatbestandsmerkmal
> des EU/CH-Datenbankherstellerrechts (sui generis, Richtlinie 96/9/EG Art. 7).
> Referenziert von `docs/tos-anti-scraping-clause.md` Ziffer 6(1) und von
> `docs/data-api-security-plan.md` Schritt 6.1.1. Arbeitsgrundlage für die
> Rechtsberatung (6.1.4), keine rechtliche Bewertung. Stand: 2026-11-14.

## 1. Umfang der Datenbank (verifiziert gegen die Produktions-DB, 2026-11-14)

| Kennzahl | Wert |
|---|---|
| Auktionshäuser/Provider | 24 |
| Auktionen | 9'078 |
| Rohdaten-Lose | 4'297'347 |
| Bereinigte, prognosefähige Preisbeobachtungen (`single_wine_prices`) | 3'232'827 |
| Aufgelöste, eindeutige Wein-Referenzen | 269'884 |
| Zeitliche Abdeckung | 1998-01-31 – 2026-11-20 (28 Jahre) |
| Datenbankgrösse (SQLite, Samsung-Disk) | 3.47 GB |

## 2. Umfang der Beschaffungs-/Aufbereitungs-Pipeline (verifiziert gegen das Repo)

| Kennzahl | Wert |
|---|---|
| Eigene Fetcher-Module (ein Modul pro Haus) | 22 (`ingest/fetchers/*.py`) + idealwine (eigener Delta-Mechanismus) + christies (eigener Backfill) |
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
