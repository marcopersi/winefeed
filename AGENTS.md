# Winefeed — Projekt-Hinweise

## Wichtige Pfade

- **Master-DB (Samsung):** `/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite`
- **Archiv (Rohdaten je Haus):** `/Volumes/samsung/winefeed-data/WeinAuktionspreise/`
- **Achtung:** Der `ARCHIVE_PATH`-Default in `data/build_db.py` und
  `data/run_ingest.py` (Google Drive `…/Meine Ablage/Wein/WeinAuktionspreise`)
  ist **veraltet** — das Archiv liegt auf der Samsung-Disk. Immer
  `ARCHIVE_PATH=/Volumes/samsung/winefeed-data/WeinAuktionspreise/` setzen.

## Manuelle Ingest-Schritte

- **Sothebys** läuft nur lokal (camoufox + residential IP, Turnstile).
  Quick-Start: `docs/runbook.md`.
- **idealwine**: läuft jetzt im CI mit (`data/run_idealwine_delta.py`,
  eigener Schritt in `ingest.yml`) — archiviert neue Zuschläge als JSON
  unter `IDealwine_normalized/_delta/` statt sie direkt in die DB zu
  schreiben, mit eigenem zeitstempel-basiertem Checkpoint
  (`ingest_manifest.json`'s `idealwine.last_sold_at`, volle ISO-Präzision --
  ein reines Datum würde Zuschläge vom selben Tag doppelt archivieren)
  statt der
  ID-basierten Standard-Dedup — die Cote-Seiten ändern sich über Zeit,
  ein einmal "erledigter" Eintrag wäre hier falsch.
- **christies** (Backfill): `data/run_christies_backfill.py` (lokal).

## Daten-Pipeline (Überblick)

- Monatlicher CI-Ingest (20 Häuser, plus iDealwine als eigener Schritt --
  siehe oben): `.github/workflows/ingest.yml` (cron `0 0 1 * *`)
  → `.github/workflows/process.yml` (DB-Build als Artifact).
- Lokaler DB-Build: `python3 data/build_db.py` (atomar, tmp + `os.replace`).
- Preis-Annotation in `data/build_db.py`: `_annotate_fx` (NLG→EUR),
  `_apply_premium_policy` (Premium/Fees), `_apply_tax` (MwSt aufs Aufgeld),
  `_fill_lot_date` (auction_date → lot_date).
