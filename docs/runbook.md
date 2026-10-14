# Runbook: manuelle Ingest-Schritte

## Sothebys manuell fetchen (Quick-Start)

**Warum manuell:** Sothebys läuft nicht in CI. Der Login nutzt `camoufox`
(löst das Cloudflare-Turnstile), und Cloudflare blockiert die Data-Center-IP
des GitHub-Runners. Der Fetch braucht daher eine lokale, residential IP.

**Einmalige Voraussetzungen:**

- Dependencies installiert (inkl. `camoufox`): `pip install -r data/requirements.txt`
- Credentials in `.env_local` (gitignored): `SOTHEBYS_USER`, `SOTHEBYS_PWD`
- Samsung-Disk gemountet (`/Volumes/samsung`)

**Ablauf (jeden Monat):**

```bash
cd data

# 1. Sothebys-Fetch (Credentials kommen automatisch aus .env_local)
ARCHIVE_PATH=/Volumes/samsung/winefeed-data/WeinAuktionspreise/ \
  python3 run_ingest.py --only sothebys

# 2. DB neu bauen (zieht die neuen Sothebys-Auktionen in die Master-DB)
ARCHIVE_PATH=/Volumes/samsung/winefeed-data/WeinAuktionspreise/ \
  python3 build_db.py
```

**Optionaler Smoke-Test** der Login-Kette (login → discover → GraphQL-Hammer):

```bash
python3 data/live_test_sothebys.py
```

## Monatlicher CI-Ingest (automatisch)

Der Rest (12 Häuser) läuft automatisch per GitHub Actions, Cron `0 0 1 * *`
(1. jedes Monats):

- `.github/workflows/ingest.yml` → fetcht, committet `data/ingest_manifest.json`,
  lädt das kumulative Archiv als Artifact hoch.
- `.github/workflows/process.yml` → baut die DB aus dem Archiv (CI-Artifact).

Der Sync vom CI-Archiv-Artifact auf die Samsung-Disk ist ein **bewusster
manueller Schritt** (CI hat keinen Zugriff auf `/Volumes/samsung`): Artifact
herunterladen, nach `/Volumes/samsung/winefeed-data/WeinAuktionspreise/`
legen, dann lokal `python3 build_db.py` laufen lassen.

Nicht in CI abgedeckt: **sothebys** (oben), **idealwine**
(`run_idealwine_delta.py`, direkter DB-Append), **christies** (Backfill
`run_christies_backfill.py`).
