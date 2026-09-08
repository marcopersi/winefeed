# Backup winefeed (Supabase) — 26.11.2022

## Was ist das?

`winefeed_supabase_backup_db_cluster-26-11-2022@00-16-41.backup.gz` ist ein
Supabase-**db_cluster**-Dump (Download über Supabase Dashboard → Database → Backups).

Inhalt:
- Supabase-Standard-Scaffolding (Rollen, `auth`/`storage`/`realtime`/`graphql`-Schemata,
  Extensionen `pgsodium`, `pg_graphql`, `pg_stat_statements`, `pgcrypto`, `pgjwt`, `uuid-ossp`, `pg_net`).
- **Eine einzige eigene Tabelle** `public."Wine"`:

| Spalte | Typ |
|---|---|
| `id` | bigint (identity) |
| `created_at` | timestamptz |
| `WineName` | varchar |
| `Region` | varchar |
| `Producer` | varchar |
| `Vintage` | smallint |
| `NoOfBottles` | smallint |
| `BottleSize` | double precision |
| `lowerPrice` | integer |
| `upperPrice` | integer |
| `hammerPrice` | integer |

## Wichtiger Befund

- **Die Tabelle ist leer** (`0` Zeilen). Es sind **keine Auktionspreise** in diesem Backup.
- **Keine JSON-Struktur** vorhanden — die Tabelle ist flach (kein `jsonb`).
- Das Backup ist ein Scaffold von 2022 und wird vom aktuellen Schema
  (`../supabase/migrations/`) überholt, das das Domain-Modell (`wine`, `offering`,
  `provider`, `rating`, `ratingagency`, `unit`, `wineoffering`) definiert.

## Wiederherstellung

Der Dump ist ein **Cluster-Dump** (`pg_dumpall`-artig, enthält `CREATE ROLE` +
`\connect template1/postgres`). Er ist für die Wiederherstellung in eine **Supabase**-Instanz
gedacht, nicht in eine nackte PostgreSQL.

### Weg A — Supabase gehostet
1. Supabase Dashboard → Projekt → Database → Backups → **Restore**.

### Weg B — Lokale Supabase-Instanz
```bash
# Dump entpacken
gunzip -c winefeed_supabase_backup_db_cluster-26-11-2022@00-16-41.backup.gz > backup.sql

# In eine laufende lokale Supabase-Postgres-Instanz laden
docker exec -i <supabase-db-container> psql -U postgres -d postgres -f - < backup.sql
```

**Verifiziert (15.08.2026):** In einer wegwerfbaren Supabase-Postgres-Instanz
(`public.ecr.aws/supabase/postgres:17.6.1`) wurde der Dump geladen:
- Die `public."Wine"`-Tabelle wurde korrekt angelegt (inkl. Primary Key).
- Viele `ERROR: role/extension already exists` sind **erwartet**, da eine Supabase-Instanz
  diese Rollen/Extensionen bereits besitzt; sie sind unkritisch.
- `SELECT count(*) FROM public."Wine"` → **0** (keine Daten).

### Fazit
Das Backup ist ladbar, enthält aber **keine Daten**. Die eigentlichen Preisdaten liegen
in den Excel-Archiven (`VinoImporter/validatedOutput/`, `priceData/import/`) und müssen
aus den Auktionsquellen nachgeladen werden. Die beschriebene **JSON-Struktur** für
Auktionspreise existiert noch nicht und muss neu entworfen werden.
