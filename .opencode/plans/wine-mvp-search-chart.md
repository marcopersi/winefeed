# Bauplan: MVP — Wein-Suche + Preis-Chart (#94)

## 1. Summary

- **Ziel:** Google-artige Eingabe → Wein auswählen → darunter die Preis-Zeitreihe
  als Chart (erstes MVP).
- **Betroffen:** neues Backend (Suche + Preise), Frontend `price-service-ui`.
- **Hauptrisiko:** Tech-Stack-Wahl und Währungs-Behandlung im Chart.
- **Business-Logik betroffen:** nein (rein lesend auf der bestehenden SQLite-DB).

## 2. Established facts

- Master-DB (SQLite, Samsung): `wines` **238.077** (`canonical_name`, `producer`,
  `region`), `lots` **2,77 M** (`hammer_price`, `buyer_premium`, `realised_price`,
  `fees`, `tax_amount`, `total_price`, `currency`, `fx_rate`,
  `fx_target_currency`, `lot_date`), `auctions` (`auction_date`), `providers`.
- Preise annotiert: `total_price = realised + fees + tax`; `fx_rate` nur für
  NLG→EUR (kein allgemeiner FX-Verlauf).
- `price-service-ui`: React 18 + Vite 8 + axios + vitest, minimales `App.jsx`.
- `priceservice`: Spring Boot 4.0.2 (früherer Prototyp, keine aktiven Endpoints).
- Kein Such-Index/FTS vorhanden; Suche muss über `canonical_name` laufen.

## 3. Scope

- **In scope:** Suche (Autocomplete auf `wines.canonical_name`/`producer`) +
  Preis-Chart (Zeitreihe `total_price` über `lot_date`).
- **Out of scope:** Auth, Admin, Filter, Bewertungen, FX-Historie, Schreiben;
  Preis-Aggregation pro Jahr (Follow-up) — das MVP zeigt rohe Lot-Punkte.
- **Unresolved (Freigabe erforderlich):** Tech-Stack (Backend + Chart) und
  Währungs-Normalisierung — siehe §7.

## 4. Evolutionary micro-steps

- **Step 1 — Backend-Grundgerüst + Suche:** FastAPI/Python, liest SQLite
  read-only via `DB_PATH` (Default `/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite`,
  `mode=ro`); `CORSMiddleware` (`allow_origins=["http://localhost:5173"]`).
  Endpoint `GET /search?q=…` liefert Top-N Treffer (`wine_id`, `canonical_name`,
  `producer`, `region`, Lot-Anzahl), sortiert Präfix-Match → Substring →
  Lot-Anzahl. Validierung: Unit-Test + manueller curl. Completion: Suche liefert Treffer.
- **Step 2 — Preis-Endpoint:** `GET /wines/{id}/prices` liefert die Zeitreihe
  (`lot_date`, `total_price`, `realised_price`, `currency`, `provider`), sortiert.
  Validierung: Unit-Test + curl. Completion: Zeitreihe korrekt.
- **Step 3 — Frontend Suche + Chart:** `price-service-ui` um eine Suchzeile
  (Debounce, Autocomplete) + ein Chart erweitern (Chart-Library: Empfehlung
  Recharts). Validierung: Vitest + manueller Lauf. Completion: Suche + Chart sichtbar.
- **Step 4 — Integration + Validierung:** Backend + Frontend gegen die echte
  Master-DB verdrahten; Stichprobe (z. B. „Château Montrose", „Sassicaia").
  Validierung: End-to-End + Tests grün. Completion: MVP benutzbar.

## 5. Validation matrix

| Betroffenes | Validierung |
|---|---|
| Backend Suche | Unit-Test + `curl /search?q=montrose` |
| Backend Preise | Unit-Test + `curl /wines/{id}/prices` |
| Frontend | Vitest + manueller Lauf (`npm run dev`) |
| Integration | End-to-End gegen Master-DB (Stichprobe) |
| Build | `npm run build` (Frontend), Backend-Test |

## 6. Risks and rollback

- **Währungs-Mix:** Lots in AUD/USD/GBP/EUR/CHF…; ohne FX-Historie zeigt das
  Chart gemischte Währungen. Rollback: Rohwährung + `currency`-Label zeigen
  (keine Konvertierung) — MVP-tauglich.
- **Suche ohne Index:** `LIKE`-Scan über 238K Namen ist ok fürs MVP; FTS als
  Follow-up bei Bedarf.
- **Nur lesend:** Backend öffnet die SQLite `mode=ro`; kein Schreibrisiko.

## 7. Approval gate

Freigegeben: **FastAPI/Python** (Backend), **Recharts** (Chart),
**Rohwährung + Label** (keine FX-Konvertierung im MVP).

## Progress

- [x] Step 1: Backend-Grundgerüst + Suche — `api/main.py` (FastAPI, SQLite
  read-only via `DB_PATH`, CORS auf `:5173`), `GET /search?q=&n=` mit
  Präfix→Substring→Lot-Anzahl. Tests `api/test_main.py` (4 grün, `api/.venv`).
  Manueller curl gegen Master-DB liefert Treffer („Montrose" 419 Lots).
- [x] Step 2: Preis-Endpoint — `GET /wines/{id}/prices` liefert
  (`lot_date`, `price` = COALESCE(total, realised), `currency`, `provider`)
  sortiert, NULL-Datum gefiltert. Tests 7 grün (Fixture). Manueller curl gegen
  Master-DB steht aus (Samsung-Disk war zwischendurch ausgeworfen).
- [x] Step 3: Frontend Suche + Chart — `price-service-ui/src/App.jsx`
  (Suchzeile mit Debounce/Autocomplete + Recharts-Linienchart), Vite-Proxy
  `/search`+`/wines` → `:8000`, Recharts installiert. Test 1 grün, `npm run
  build` ok. End-to-End via Proxy verifiziert (curl auf `:5173/search`).
- [~] Step 4 (teilweise): Backend live gegen die Prod-DB verifiziert
  (`curl /search?q=montrose`, `=sassicaia`, `/wines/top?n=3` — alle liefern
  plausible Treffer). Frontend nicht erneut gefahren (`npm run dev` steht
  noch aus). Dabei einen Merge-Qualitäts-Fund entdeckt und gefixt (s.
  `wine-pipeline-v2.md` Review-Befund 5): „Sassicaia" zerfiel in 13+
  separate `wines`-Zeilen — kein Bug dieses MVP-Plans, sondern eine
  §4-Normalisierungslücke, die erst durch den echten Suchtest sichtbar
  wurde.
