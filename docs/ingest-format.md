# Ingest-Format: Fetcher → Loader Vertrag

Dieses Dokument definiert das kanonische Datenformat, das `data/build_db.py`
von jedem Fetcher erwartet, und die Mapping-Tabelle pro Haus.

## Kanonisches Format

Jede archivierte Auktions-Datei ist ein JSON-Objekt mit zwei Schlüsseln:

```json
{
  "auction": { "id": "...", "name": "...", "date": "YYYY-MM-DD",
               "currency": "EUR", "price_basis": "HAMMER", "location": "..." },
  "lots": [
    { "lot_no": "...", "wine": "...", "producer": "...", "region": "...",
      "vintage": 2019, "quantity": 3, "bottle_size_dl": 7.5,
      "estimate_low": 100.0, "estimate_high": 200.0,
      "hammer_price": 150.0, "realised_price": null,
      "price_basis": "HAMMER", "currency": "EUR", "sold": 1,
      "description": "...", "condition_text": "..." }
  ]
}
```

- `auction` ist ein Objekt; `lots` ist eine **Liste** (nie ein Dict).
- Feldnamen variieren je Haus; die Loader in `build_db.py` sind die
  verbindliche Spezifikation (siehe Tabelle unten).
- `price_basis`: Die Loader setzen derzeit ausschließlich `HAMMER`,
  `HAMMER_PLUS_BUYERS_PREMIUM` und `UNKNOWN` (vereinzelt `None`). Die Werte
  `TOTAL` und `REPORTED_REALIZED` sind im Datenmodell vorgesehen, werden aber
  aktuell von keiner Quelle erzeugt — nicht als Zielwert annehmen. Das Schema
  erzwingt den Enum nicht (`TEXT` ohne `CHECK`); der Default wird pro Loader
  explizit gesetzt, es gibt keinen globalen Default.

## Mapping-Tabelle

Legende: ✓ konsistent · ✗ muss gemappt werden · ⇧ Fetcher/Parser muss mehr
Felder extrahieren · ＋ Loader fehlt (neu bauen).

| Haus | Fetcher/Parser liefert (roh) | Loader erwartet | Status |
|---|---|---|---|
| weinauktionator | Parser `{auction{id,name,date}, lots{lot_no,region,wine,hammer_price,format}}` | identisch (`load_weinauktionator`) | ✓ |
| hdh | Parser extrahiert jetzt `vintage`, `wine`, `estimate_low`, `estimate_high`; liefert zusätzlich `lot_no,qty,description,estimate,hammer,aggregate` | `load_hdh` liest außerdem `grower,size,mixed_lot,condition` — diese liefert das PDF nicht strukturiert, bleiben `NULL` | ⇧ |
| langtons | `fetch` mappt auf `auction{id,name,date}` + `lots{lot,wine,region,classification,vintage,quantity,winning_bid,currency,notes}` | identisch (`load_langtons`) | ✓ |
| winefields | `fetch` mappt auf `auction{auction_id,title,time_start}` + `lots{lot_no,title,producer,quantity,size,estimate_low,estimate_high,hammer,status,is_mixed_lot,condition,currency}` | identisch (`load_winefields`); `producer`/`size` bleiben `None` (nicht im `result_page`) | ✓ |
| dorotheum | `fetch` mappt `lots`-Dict auf Liste `{lot_nr,name,estimate,realized_price,sold,currency,description}` (europ. Zahlenformat) | identisch (`load_dorotheum`) | ✓ |
| pandolfini | `fetch` mappt auf `auction{id,name,date}` + `lots{lot_nr,name,estimate_low,estimate_high,sold_price{class,value},description}` | identisch (`load_pandolfini`); `estimate_low/high` bleiben `None` (nicht im JSON-LD) | ✓ |
| sothebys | `fetch` mappt auf `auction{auction_id,title,dates,currency,location}` + `lots{lot_number,title,estimate_low,estimate_high,hammer_price,final_price,sold,currency}`; `final_price = hammer × 1.25` | identisch (`load_sothebys`) | ✓ |
| finarte | `lots` roh `{stringa_filtro_autore_lotto,anno,prezzo_aggiudicazione,valore_base_asta,base_asta,…}` | `auction{slug,name,date}` + `lots{lot_nr,name,region,vintage,estimate_min,estimate_max,hammer_price,sold,currency,vat_regime}` | ⇧ erweitern + map (Step 3) |
| besch-cannes | `lots{lot_no,hammer,estimate,url}` | `auction{id,slug,date,currency,price_basis}` + `lots{lot_no,appellation,vintage,estimate[list],hammer/adjuge,description,remarks}` | ⇧ erweitern + map (Step 3) |
| dobiaschofsky | `lots{name,hammer,auction,url}` | `auction{id,name,date}` + `lots{lot_nr,name,vintage,estimate_chf,hammer_chf,description}` | ⇧ erweitern + map (Step 3) |
| koppe | `lots{name,vintage,region,color,bottle_size,format,hammer_price,hammer_price_raw,estimate}` | **kein Loader** | ＋ `load_koppe` bauen (Step 4) |
| weinauktion (steinfels/weinboerse) | `{title,date,currency,auction_meta,lots(items)}` (rohe API-Items) | `load_steinfels` liest nur Alt-XLSX; kein `load_weinboerse` | ＋ Loader bauen, XLSX↔JSON klären (Step 4) |

## Verzeichnisname: provider ↔ Loader-Hausname

`data/orchestrate.py:_write_json` schreibt nach `ARCHIVE/<provider>`
(Provider-Name des Fetchers, lowercase), während die Loader über
`_json_files("<Haus>")` aus `ARCHIVE/<Haus>` (CamelCase/abweichend) lesen.
Diese Namen müssen übereinstimmen, sonst laden die Loader die neuen Dateien
nicht. Betroffen (provider → Loader-Verzeichnis):

| provider | Loader `_json_files` |
|---|---|
| hdh | `HDH` |
| langtons | `Langtons` |
| winefields | `Winefields` |
| dorotheum | `Dorotheum` |
| pandolfini | `Pandolfini` |
| finarte | `Finarte` |
| besch-cannes | `BeschCannes` |
| dobiaschofsky | `Dobiaschofsky` |
| sothebys | `Sothebys` |
| weinauktionator | `weinauktionator` (✓) |

Fix gehört zu Step 2: ein zentrales Mapping `provider → archive_dir` im
Orchestrator, damit neue Fetcher-JSONs im Loader-Verzeichnis landen (bzw. die
Loader-Namen vereinheitlicht werden). Entscheidung offen, wird in Step 2
geklärt.

## idealwine (Sonderweg, nicht über diese Kette)

idealwine wird **nicht** über `run_ingest`/`build_db`-Loader abgewickelt. Der
Fetcher (`ingest/fetchers/idealwine.py`) liefert `productVintageRatings`
(kein `{auction, lots}`); die eigene Pipeline `data/run_idealwine_delta.py`
→ `idealwine_diff.py` normalisiert und schreibt **direkt** in die DB
(`Builder.insert_new_lots`), ohne `build_db`-Rebuild. `load_idealwine`
(`build_db.py:948`) liest stattdessen einen abweichenden Bestand
(`IDealwine_normalized`) und ist nicht Teil dieses Nachlade-Scopes. idealwine
ist daher aus `run_ingest.PROVIDERS` entfernt (Entscheidung D1).

## Offene Punkte (in den folgenden Schritten zu klären)

1. **hdh**: `grower`, `size`, `mixed_lot`, `condition` liefert das PDF nicht
   strukturiert — bleiben `NULL` im `load_hdh`. Wäre nur über ein erweitertes
   PDF-Parsing (Lot-Beschreibungstext) erreichbar; aktuell bewusst offen.
2. **Vollständige Roh-Feldlisten** für `finarte.__DATI_LOTTI__` und
   `weinauktion`-API-Items sind nur teilweise aus den Test-Fixtures bekannt.
   Die vollständige Liste ist beim Normalisieren (Step 3/4) live bzw. gegen
   einen echten Payload zu verifizieren.
3. **Sothebys `final_price = hammer × 1.25`** ist eine Flat-Approximation. Die
   reale Buyer's Premium ist gestaffelt (26 %/21 %/14,5 % je Betrag und
   Währung); exakte `final_price` bleibt bis zu einer verlässlichen Quelle
   offen (GraphQL liefert `ResultHidden`).
4. **Pandolfini `estimate_low/high`** und **Winefields `producer`/`size`** sind
   nicht im Roh-Payload vorhanden — bleiben `None`.
5. **weinauktion-Altbestand**: `load_steinfels` liest historische XLSX; die
   neuen API-Items müssen auf dieselbe Spaltenstruktur gemappt oder ein
   separater `load_weinboerse`/`load_steinfels_json` gebaut werden (Step 4).
6. **Fail-loud bei leerem Fetch** (z. B. Sothebys ohne `Auction`-Eintrag →
   `{"auction": {}, "lots": []}` wird trotzdem als „gefetcht" markiert) — wird
   in Step 7 (Guardrails) adressiert.
