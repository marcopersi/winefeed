# Bauplan: Lots/Auktions-Attribute vervollständigen (location, Währung, Premium, Fees, MwSt) + CI↔Samsung

Stand: 2026-10-13

---

## 1. Summary

**Ziel:** Das Datenmodell so vervollständigen, dass pro Lot **netto Hammer,
Premium, Brutto, Fees, MwSt** und pro Auktion **location/currency** sauber
vorliegen; danach den CI-Pfad mit der Samsung-Master-DB verbinden. Motiv: die
Daten sind für Investitions-/FX-/Arbitrage-Auswertungen gedacht — dafür müssen
Brutto-Preise (inkl. Premium/Fees/MwSt) und Währungen zuverlässig sein.

**Betroffen:** Schema (neue Preisfelder), Loader/Fetcher (Attribute),
`build_db.py`, `run_idealwine_delta.py`, CI-Workflows, ein einmaliger
Re-Normalisierungs-Lauf.

**Hauptrisiken (absteigend):**
1. Falsche Premium-Prozentsätze (bis 25 % Brutto-Differenz)
2. Stiller Datenverlust beim Re-Normalisieren
3. FX-/Währungsfehler (historische Währungen)
4. CI↔Samsung laufen auseinander

---

## 2. Established Facts (live aus der Samsung-DB geprüft)

1. `lots.currency` existiert und ist gefüllt: AUD 1 342 478 · USD 622 798 ·
   GBP 282 448 · EUR 276 637 · HKD 108 680 · CHF 98 887 · SGD 30 061 ·
   **NLG 6 188** · CNY 137 · **NULL 7 444** (v. a. winebarrel).
2. `auctions.location` nur für **christies (845/845)** und
   **sothebys (286/286)**; die anderen 17 Häuser → NULL.
3. `price_basis`: HAMMER 2 597 910 · HAMMER_PLUS_BUYERS_PREMIUM 177 846 ·
   UNKNOWN 2.
4. `buyer_premium` praktisch leer (5 560 von 2,78 Mio); `realised_price` nur
   485 k gefüllt. **Kein** `fees`-/`tax_amount`-Feld vorhanden.
5. Fixe Location/Currency (ortsgebunden): weinboerse/steinfels/baghera/
   dobiaschofsky/wermuth-sa = CH/CHF; koppe = DE/EUR; finarte/pandolfini =
   IT/EUR; besch-cannes = FR/EUR; dorotheum = AT/EUR; hdh = US/USD;
   langtons = AU/AUD; weinauktionator = DE/EUR.
6. CI (`ingest.yml`/`process.yml`) und lokaler `build_db` sind **getrennt**:
   CI produziert ein DB-**Artifakt**, lokal schreibt `build_db` direkt auf
   Samsung. Kein Sync-Mechanismus.
7. Sothebys-Premium belegt: 24 % + 1 % Overhead (`final_price = hammer × 1.25`);
   Pandolfini/Zacky sind `HAMMER_PLUS_BUYERS_PREMIUM` (inkl. Aufgeld),
   HDH `aggregate` inkl. Aufgeld. Übrige Premiums/Fees/MwSt nicht erfasst.

---

## 3. Scope

### In Scope

- Datenmodell (Preis-Struktur) erweitern
- Attribut-Befüllung: location, currency, Premium, Fees, MwSt
- Re-Normalisierungslauf gegen die Master-DB
- CI↔Samsung-Synchronisierung

### Out of Scope

- Applikation (Search/FX/Arbitrage) — folgt später
- Wechselkurs-Verlauf (ist Applikationslogik, nicht Datenattribut)

### Offene Entscheidungen

- **(D1) Preis-Modell:** flache Spalten (`buyer_premium`, `fees`,
  `tax_amount`, `total_price`) **oder** separate `price_components`-Tabelle.
  Empfehlung: flache Spalten für Premium/Fees/Tax, `total` berechnet.
  **Achtung:** Gross-only Häuser (Pandolfini, Zacky, HDH-aggregate) liefern
  keinen Hammer — `total_price` kann dann nicht abgeleitet werden. Invariante
  definieren: `price_source` Marker (`OBSERVED` vs. `DERIVED`) je Preisfeld,
  plus Regel welches Feld autoritativ ist pro `price_basis`.
- **(D2) CI↔Samsung — entschieden (Option c):** CI produziert nur das
  kumulative Archiv-Artefakt + committet `data/ingest_manifest.json`; lokal
  baut `build_db.py` die Master-DB (Samsung) aus dem Archiv. **Ein geteiltes
  Manifest** (`data/ingest_manifest.json`) für Backfill, lokalen `run_ingest`
  und CI — damit kein Doppel-Fetch und keine Manifest-Drift. Der Sync
  (CI-Artefakt → Samsung-Archiv) bleibt ein bewusster manueller Schritt.
- **(D3) Premium-/Währungs-Quelle:** je Haus aus Primärquelle (Terms/Conditions)
  verifizieren — nicht raten. Historische Währungen: NLG→EUR hat gesetzlichen
  Fixkurs (2,20371) — **beides speichern**: Rohwährung + `fx_rate` +
  `fx_target_currency` wo gesetzlicher Kurs existiert. Damit ist der
  Währungs-Teil von D3 entschieden; offen bleibt nur die Premium-Quelle.

---

## 4. Nicht-funktionale Anforderungen (Guardrails)

- **NFR-1 Vollständigkeit:** jedes Haus belegt location + currency +
  Premium-Policy, oder explizit als „keine/unknown" markiert. Kein stilles NULL.
- **NFR-2 Korrektheit Premium:** Prozentsätze aus Primärquelle; Cross-Check
  `realised ≈ hammer × (1 + premium)` wo möglich.
- **NFR-3 FX/Temporal:** Währung + Auktionsdatum zusammen; historische
  Währungen (NLG) gemäß D3 explizit behandeln. **Bekannte Lücke:**
  `auctions.auction_date` ist NULL für winebarrel (virtuelle Einzel-Auktion)
  und idealwine "cote"-Auktionen — dieselben ~7 444 NULL-currency Lots.
  Lot-Level `lot_date` als Fallback definieren.
- **NFR-4 Idempotenz Re-Normalisierung:** Wiederholungslauf strukturell
  identisch (Tabellen-Level Checksummen exkl. Build-Metadaten, da
  `builds.started_at`/`completed_at` nicht determinisch sind);
  `UNIQUE`-Gates greifen.
- **NFR-5 Fail-loud:** fehlende Pflicht-Attribute → Skip + Report, kein
  stummer Teil-Import.
- **NFR-6 CI↔Samsung-Konsistenz:** Master-DB hat genau einen Besitzer; Sync
  idempotent + atomar (temp + replace), keine Teil-Überschreibung.

---

## 5. Evolutionary Micro-Steps

1. **Gebührenstruktur je Haus ermitteln** (Premium %, Fees, MwSt) aus
   Primärquellen → Ground-Truth-Tabelle `docs/premium-policy.md`.
2. **Schema erweitern** (D1): `buyer_premium`, `fees`, `tax_amount`,
   `total_price` (oder `price_components`).
3. **Location/Currency je Haus befüllen** (fixe Zuordnung + historische
   Währungen gemäß D3).
4. **Premium/Fees/Tax in Loader/Fetcher** einspeisen (Muster = bestehende Loader).
5. **Re-Normalisierungslauf** gegen die Master-DB (idempotent, Fail-loud) +
   NFR-Checks.
6. **CI↔Samsung-Sync** gemäß D2 implementieren.
7. **Senior-Review + Fixes.**

---

## 6. Validation Matrix

| Betroffenes | Validierung | NFR |
|---|---|---|
| Schema | `PRAGMA integrity_check`, `foreign_key_check` | — |
| Premium | `realised ≈ hammer × (1+premium)` Stichprobe je Haus | NFR-2 |
| Location/Currency | Vollständigkeits-Query (0 NULL je Haus) | NFR-1 |
| Idempotenz | Wiederholungslauf → 0 Änderungen | NFR-4 |
| CI↔Samsung | Sync-Dry-Run + Prüfsummen-Vergleich | NFR-6 |
| Backfill-Coverage | `N_discovered` vs. Ground-Truth Sale Count; Ambiguous-Titel-Review-File nicht leer = Completeness-Gap | NFR-1 |
| Lint | Pylint | — |

---

## 7. Risks and Rollback

- **Falsche Premium (bis 25 %):** NFR-2 + Ground-Truth-Policy; Rollback =
  DB-Backup.
- **Re-Normalisierung verliert Daten:** atomarer Build (temp + replace) +
  vorheriges Backup.
- **FX-Fehler:** NFR-3; historische Währungen explizit behandeln.
- **Sync-Konflikt:** NFR-6 (ein Besitzer); Rollback = letzter Stand.

---

## 8. Approval Gate

Freigabe für Gesamtscope + **D1** (Preis-Modell), **D2** (CI↔Samsung),
**D3** (Premium-/Währungs-Quelle). Danach `PLANNING → IMPLEMENTING`.
