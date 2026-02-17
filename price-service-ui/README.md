# Price Service UI (Vite)

Dieses UI läuft mit Vite + React und verwendet Vitest für Tests.

## Scripts

Im Verzeichnis `price-service-ui`:

- `npm start` oder `npm run dev` startet den Dev-Server.
- `npm run build` erstellt den Produktions-Build.
- `npm run preview` startet eine lokale Vorschau des Builds.
- `npm test` führt die Vitest-Tests einmalig aus.

## Backend Proxy (Dev)

Für lokale API-Aufrufe ist in `vite.config.js` ein Proxy auf `http://localhost:8081` konfiguriert für:

- `/api`
- `/prices`
