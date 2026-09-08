# winefeed

Stand: 15. August 2026

## Überblick

Dieses Repository enthält mehrere Teilprojekte rund um Wein-Preisdaten:

| Teilprojekt | Typ | Zweck |
|---|---|---|
| `VinoDomain` | Java-Library | Domain-Modell (`Wine`, `Offering`, `Provider`, `Rating`, `RatingAgency`, `Unit`, …) |
| `PersiCommons` | Java-Library | `ExcelUtil` (Apache POI) |
| `VinoImporter` | Java | **Maßgebliche Importer-Implementierung** für Steinfels, Wermuth, Weinboerse (Tika/PDFBox/iText) |
| `priceservice` | Spring Boot 4.0.2 | REST + JPA + PostgreSQL (früher Prototyp) |
| `price-service-ui` | React/Vite | Frontend zu `priceservice` |
| `priceData` | Python + Supabase | Experimenteller Parser/Import (redundant zu `VinoImporter`) |
| `Sylvies Parser` | Python | Ad-hoc-Web-Scraper, standalone |
| `archive/` | — | Legacy-Projekte (`VinoDao`, `VinoGUI`, `OldSourceVino`) |

## Build

Alle Gradle-Module (`PersiCommons`, `VinoDomain`, `VinoImporter`, `priceservice`) sind
Subprojekte eines einzigen Root-Builds. `VinoImporter` hängt direkt von `VinoDomain`
und `PersiCommons` ab (kein `mavenLocal`-Publishing nötig).

```bash
# Alle Gradle-Module bauen und testen (Java 17)
./gradlew build

# Einzelnes Modul bauen
./gradlew :VinoImporter:build

# price-service-ui bauen (npm, separat)
npm install --prefix price-service-ui
npm run build --prefix price-service-ui
```

## Status je Teilprojekt

### VinoImporter
- **Code vorhanden:** Ja. Import-Strategie über `ImportingStrategy`/`Task` (Spring `@Component`).
- **Importer:** `steinfels/`, `wermuth/` (format2015, formatpre2015), `weinboerse/`.
- **Ausgabe:** `validatedOutput/*.csv` und `validatedOutput/vinoStagingFile2015-2008.xlsx`.
- **Tests:** Steinfels- und Wermuth-Tests vorhanden. Hinweis: `WermuthPre2015Tests` referenziert
  `prototyping/resources/223.pdf`, das nicht (mehr) existiert.
- **Build:** Läuft, sofern `VinoDomain` und `PersiCommons` vorher nach `mavenLocal` publiziert wurden.

### priceservice
- **Code vorhanden:** Ja. `PriceserviceApplication` startet REST-API auf Port 8081.
- **Endpoints:**
  - `POST /api/upload` — liest Excel und schreibt pro Zeile in `price_data`
    (`FileUploadController`).
  - `GET /prices/search?keyword=...` — Suche in `column1` (`PriceController`).
- **Build:** Läuft (`./gradlew clean build`, Tests grün via H2-Profil).
- **Achtung:** Früher Prototyp. `PriceData` ist generisch (`column1`/`column2`), kein Bezug
  zu `VinoDomain`. DB-Credentials sind in `application.properties` hardcodiert; zum Starten
  wird eine laufende PostgreSQL auf Port 5432 benötigt.

### price-service-ui
- **Code vorhanden:** Ja. Vite + React + Vitest (aus CRA migriert).
- **Proxy:** `/api` und `/prices` → `http://localhost:8081` (siehe `vite.config.js`).
- **Build:** `npm run build`.

### priceData
- **Code vorhanden:** Ja. Python + Supabase (lokale Instanz über `supabase start`).
- **Inhalt:** Steinfels-Parser (315–324), Wermuth-Staging-Excel, Supabase-Migrationen.
- **Status:** Redundant zu `VinoImporter`. Bereinigung offen — siehe `CLEANUP_PLAN.md`.

### Sylvies Parser
- **Code vorhanden:** Ja (`Sylvies Parser/sylviesParser.py`).
- **Integration:** Standalone, keine Anbindung an die übrigen Module.

## Aufräumen

Siehe `CLEANUP_PLAN.md` für den Stand der Bereinigung (tote Dateien, Altlasten,
Redundanzen, Dokumentation).
