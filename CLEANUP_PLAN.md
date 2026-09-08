# Cleanup-Plan winefeed

Stand: 15. August 2026 · Status: **erledigt** (bis auf 4 optionale Folgenpunkte unten).

## Bestandsaufnahme (Kurzfassung)

| Teilprojekt | Art | Status |
|---|---|---|
| `VinoDomain` | Java-Domain-Modell (Wine, Offering, Provider, Rating, …) | Library (Gradle-Subprojekt) |
| `PersiCommons` | `ExcelUtil` (Apache POI) | Library (Gradle-Subprojekt) |
| `VinoImporter` | Importer für **Steinfels**, **Wermuth**, **Weinboerse** (Tika/PDFBox/iText) | Aktiv, Tests vorhanden |
| `priceservice` | Spring Boot 4.0.2, REST + JPA + PostgreSQL | Prototyp, baut grün, braucht laufende DB |
| `price-service-ui` | React/Vite-Frontend (aus CRA migriert) | Frontend zu `priceservice` |
| `priceData` | Python + Supabase (Steinfels-Parser 315–324, Wermuth-Staging, Migrationen) | Redundant zu `VinoImporter` |
| `Sylvies Parser` | Einzelnes Python-Scraper-Skript | Standalone, nicht integriert |
| `archive/` | `VinoDao.zip`, `VinoGUI.zip`, `OldSourceVino.zip` | Legacy (ausgelagert 28.01.2026) |

**Grundsatzentscheidung:** Java (`VinoImporter`) ist die maßgebliche Importer-Implementierung.

---

## 1. Importer-Redundanz auflösen (Java maßgeblich) — ERLEDIGT (archiviert)

**Prüfergebnis (Redundanz-Check):** Python (`priceData`) und Java (`VinoImporter`)
parsen dieselben Steinfels-/Wermuth-Quellen und extrahieren ~90 % dieselben Felder.
Unterschiede:
- Python-Steinfels trennt zusätzlich **Producer** und **Classification** (Java tut das nicht).
- Java hat das reichere `Offering`-Modell (Auktionsdatum, Event-ID, min/max-Preis).

**Entscheidung:** archivieren (reversibel). Verschoben nach `archive/priceData-parser/`:
- [x] `priceData/src/` → `archive/priceData-parser/src/`
- [x] `priceData/vino_excel_importer.py`, `test_all_parsers_unit_fix.py`, `README_DOMAIN_MODEL.md`
- [x] `priceData/archive/` (alte Parser-Iterationen) → `archive/priceData-parser/old/`

Verblieben in `priceData/` (Daten + Supabase):
- `import/` (Quell-PDFs + Excel-Resultate — die Daten-Archive)
- `supabase/` (Migrationen), `supabase_config.py`, `requirements.txt`, `start_supabase.sh`
- Hinweis: `priceData/import/Wermuth/prepared/vinoStagingFile2015-2008.xlsx` liegt
  vermutlich doppelt zu `VinoImporter/validatedOutput/vinoStagingFile2015-2008.xlsx`.

## 2. Tote/leere Dateien — ERLEDIGT

- [x] `priceData/analyze_quality.py` (0 Bytes) — entfernt.
- [x] `priceData/check_years_in_data.py` (0 Bytes) — entfernt.
- [x] `priceData/README.md` — auf tatsächliche Dateien korrigiert.
- [x] `priceData/src/README.md` — `archive/`-Verweis korrigiert.

## 3. VinoImporter-Altlasten — TEILWEISE ERLEDIGT

- [x] `VinoImporter/app/` — Hello-World-Stub entfernt.
- [x] `VinoImporter/bin/` — Duplikat von `resources/` entfernt.
- [x] `VinoImporter/prototyping/` — PDF-Parser-Experimente entfernt.
- [x] `VinoImporter/tables/**/*.hbm.xml` — alte Hibernate-Mappings entfernt (in Git-Historie).
- [x] `VinoImporter/QualityCheckPending/` — Reste (PDFs + `.DS_Store`) entfernt.
- [x] Dependency auf `mavenLocal` durch Gradle-Projekt-Dependencies ersetzt.
      Einheitlicher Root-Build: `VinoImporter` hängt via `project(":VinoDomain")`/`project(":PersiCommons")`
      ab; `maven-publish` + `mavenLocal()` entfernt; Modul-Wrapper/Settings entfernt; CI auf ein
      `./gradlew build` reduziert. Validierung: `./gradlew clean build` grün.

## 4. Wurzel-Dokumentation — TEILWEISE ERLEDIGT

- [x] `README.md` aktualisiert (Module, Build, Status, Hinweis auf Cleanup).
- [x] `.jscpd.json` entfernt (verwaist, jscpd aus CI entfernt).
- [x] `ACT_TESTING.md` korrigiert (verwaister `owasp-dependency-check`-Job entfernt).
- [ ] Doppelten Git-Commit bereinigen — **zurückgestellt** (Historie-Rewrite erfordert Rebase +
      Force-Push; riskant, kein zwingender Nutzen).

## 5. Git-Hygiene — ERLEDIGT

- [x] 2 getrackte `.DS_Store` entfernt (über Löschung von `QualityCheckPending/`).
- Hinweis: `.gradle/file-system.probe` ist versehentlich getrackt — sollte in `.gitignore`.

---

## Noch zu tun

1. Optional: Duplikat-Commit bereinigen — aktuell **ignoriert** (Historie-Rewrite, kein Nutzen).
2. `.gradle/`-Artefakte aus Tracking entfernt (`git rm --cached`, 5 Dateien). ERLEDIGT.
3. `priceData/supabase/` + `supabase_config.py` — **offen, aktuell untouched**.
4. `priceData/requirements.txt` bereinigt (nur `supabase` + `python-dotenv`). ERLEDIGT.
