# winefeed

Stand: 28. Januar 2026

## Überblick

Dieses Repository enthält mehrere Teilprojekte:

- **price-service-ui**: React (Create React App) Frontend
- **priceservice**: Spring Boot Backend (REST + JPA)
- **priceData**: Python/Supabase Datenmodell, Importer und Parser
- **Sylvies Parser**: Ad‑hoc Web‑Scraper (Python)

## Status je Teilprojekt

### price-service-ui

- **Code vorhanden:** Ja. Siehe [price-service-ui/src/App.js](price-service-ui/src/App.js) und [price-service-ui/src/index.js](price-service-ui/src/index.js).
- **Build läuft:** Nicht verifiziert. Aktuell ist [price-service-ui/package.json](price-service-ui/package.json) **kein gültiges JSON** (fehlendes Komma zwischen `web-vitals` und `react-scripts`). Dadurch schlagen `npm install`/`npm run build` sehr вероятet fehl. Zusätzlich ist `react` 19.x mit `react-dom` 18.2.0 gemischt, was weitere Inkompatibilitäten verursachen kann.
- **Verbindung zu priceservice:** Ja, über CRA‑Proxy. `proxy` ist auf `http://localhost:8081` gesetzt und die UI ruft `POST /api/upload` sowie `GET /prices/search` auf. Diese Endpoints existieren im Backend (siehe [priceservice/src/main/java/ch/persi/wine/feed/priceservice/controller/FileUploadController.java](priceservice/src/main/java/ch/persi/wine/feed/priceservice/controller/FileUploadController.java) und [priceservice/src/main/java/ch/persi/wine/feed/priceservice/controller/PriceController.java](priceservice/src/main/java/ch/persi/wine/feed/priceservice/controller/PriceController.java)).

### priceservice

- **Code vorhanden:** Ja. Einstieg über [priceservice/src/main/java/ch/persi/wine/feed/priceservice/PriceserviceApplication.java](priceservice/src/main/java/ch/persi/wine/feed/priceservice/PriceserviceApplication.java).
- **Build läuft:** Nicht verifiziert. Es gibt ein Gradle‑Setup in [priceservice/build.gradle.kts](priceservice/build.gradle.kts). Für Lauf/Tests wird eine PostgreSQL‑DB benötigt (siehe [priceservice/src/main/resources/application.properties](priceservice/src/main/resources/application.properties)). Ohne laufende DB wird das Spring‑Boot‑Startup fehlschlagen.
- **API‑Oberfläche:**
	- `POST /api/upload` liest Excel‑Dateien und schreibt pro Zeile in die DB ([FileUploadController.java](priceservice/src/main/java/ch/persi/wine/feed/priceservice/controller/FileUploadController.java)).
	- `GET /prices/search?keyword=...` sucht in `column1` ([PriceController.java](priceservice/src/main/java/ch/persi/wine/feed/priceservice/controller/PriceController.java)).

### priceData

- **Code vorhanden:** Ja. Siehe u. a. [priceData/vino_excel_importer.py](priceData/vino_excel_importer.py) und [priceData/supabase_config.py](priceData/supabase_config.py).
- **Build läuft:** Nicht zutreffend (Python‑Skripte). Ausführung setzt eine lokale Supabase‑Instanz sowie `.env` voraus (siehe [priceData/README.md](priceData/README.md)).
- **Was wurde erstellt:**
	- **Supabase‑Schema & Migrations** in [priceData/supabase/migrations](priceData/supabase/migrations) (mehrere Versionen, inkl. Domain‑Model‑Portierung).
	- **Domain‑Model‑Dokumentation** in [priceData/README_DOMAIN_MODEL.md](priceData/README_DOMAIN_MODEL.md).
	- **Excel‑Importer**: [priceData/vino_excel_importer.py](priceData/vino_excel_importer.py) importiert Excel‑Daten in das Supabase‑Schema.
	- **Parser‑Basis & Tools** unter [priceData/src](priceData/src):
		- Steinfels‑Parser inkl. 2002‑Set (315–319) und Unit‑Erkennung (siehe [priceData/src/README.md](priceData/src/README.md)).
		- Unit‑Fix‑Tests: [priceData/test_all_parsers_unit_fix.py](priceData/test_all_parsers_unit_fix.py).
	- **Leere Platzhalter‑Skripte:** [priceData/analyze_quality.py](priceData/analyze_quality.py) und [priceData/check_years_in_data.py](priceData/check_years_in_data.py) sind aktuell leer.

### Sylvies Parser

- **Code vorhanden:** Ja. Ein einzelnes Skript in [Sylvies Parser/sylviesParser.py](Sylvies%20Parser/sylviesParser.py).
- **Build läuft:** Nicht zutreffend (Python‑Skript). Es gibt keine Requirements‑Datei; das Skript erwartet `requests` und `beautifulsoup4` (siehe Imports).
- **Integration:** Standalone‑Scraper, aktuell keine Anbindung an priceData oder priceservice.

## Offene Punkte / nächste Schritte

- **price-service-ui**: `package.json` reparieren (JSON‑Syntax + Abgleich `react`/`react-dom` Versionen) und Build testen.
- **priceservice**: Datenbank‑Konfiguration prüfen (Credentials/DB existieren?) und Start prüfen.
- **priceData**: Leere Skripte füllen oder entfernen; Parser‑Coverage für 316–319 finalisieren; Import‑Pipeline klären.
- **Sylvies Parser**: Abhängigkeiten dokumentieren und entscheiden, ob/wo es integriert wird.
