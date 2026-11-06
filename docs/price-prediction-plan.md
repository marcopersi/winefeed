# Bauplan: Preis-Prognose (probabilistisch) für Weine mit genügend Auktionspreisen

Stand: 2026-10-29 · Status: Entwurf zur Freigabe · Sprache/Format analog `christies-backfill-plan.md`

---

## 1. Summary

**Ziel:** Für Wein+Jahrgang-Kombinationen mit ausreichend Preishistorie eine
**Prädiktionsverteilung** des nächsten Auktionspreises liefern, nicht einen
Einzelwert: z. B. „80 % Intervall: CHF X–Y, Median Z". Dünne Fälle bekommen
einen Fallback auf einen Gruppenindex mit breiterem Intervall – oder gar keine
Prognose (explizites `INSUFFICIENT_DATA`).

**Ansatz (gestuft, jede Stufe einzeln lieferbar und messbar):**

| Stufe | Modell | Zweck |
|---|---|---|
| 0 | Daten-Grundlage (Preis je 0,75 l in EUR, bereinigte Daten) | Voraussetzung, **grösster Hebel** |
| 1 | Baselines (Naiv, letzter Median, gleitender Median) | Messlatte, die das Modell schlagen muss |
| 2 | Local-Level-Modell (Kalman, Log-Preis, unregelmässige Abstände) | Kernmodell für dichte Serien |
| 3 | Gruppenindex (Repeat-Sales/Hedonic nach Produzent·Region·Jahrgang) | Fallback für dünne Serien + Trend-Kovariate |
| 4 | Konforme Kalibrierung der Intervalle | Garantierte, empirisch belegte Abdeckung |
| 5 | Serving (Tabelle + API-Endpoint + UI) | Nutzbarkeit |

**Hauptrisiken (absteigend):**

1. **Datenqualität statt Modell:** `price_per_bottle` ist in der Master-DB in
   *allen* Zeilen NULL, `bottle_size_dl` zu ~90 % NULL, FX nur für NLG befüllt
   (siehe §2). Ohne Stufe 0 ist jede Prognose Scheingenauigkeit.
2. **Scheingenauigkeit / zu enge Intervalle:** Auktionsrauschen (Zustand,
   Haus, Premium) wird in Prozessrauschen verwechselt.
3. **Look-ahead-Leck in der Evaluation:** Zufälliges statt zeitliches Splitten
   macht jedes Modell scheinbar gut.
4. **Selektions-Bias:** Nur *verkaufte* Lose haben Preise; Rückgänge (`sold=0`)
   zensieren die Verteilung nach unten.
5. **Dedup-/Duplikat-Effekte:** Gleiche Lose aus mehreren Quellen
   (z. B. idealwine „cote" vs. Haus) verzerren Serien.

**Betroffene Module:**

| Modul | Änderung |
|---|---|
| `data/build_db.py` | Nur Stufe 0: `price_per_bottle`, FX-Annotation, `lot_date`-Normalisierung (separate Reviews, siehe §5) |
| `data/forecast/` | **NEU** – Paket (Features, Modelle, Evaluation, Runner) |
| `data/tests/test_forecast_*.py` | **NEU** |
| `api/main.py` | Stufe 5: Endpoint `/wines/{id}/forecast` |
| `price-service-ui/src/App.jsx` | Stufe 5: Fan-Chart |
| `data/requirements.txt` | `statsmodels`, `numpy`, `pandas`, `scipy` (heute **nicht installiert**) |
| `docs/premium-policy.md` | Referenz, keine Änderung |

---

## 1a. Fortschritts-Übersicht & nächste Schritte (Stand 2026-11-05)

Dieser Block wird bei jedem Review-Durchlauf aktualisiert — Detail-Status
und Zahlen stehen bei den jeweiligen Micro-Steps in §5.

| Stufe/Schritt | Status |
|---|---|
| 0.1 Datumsbereinigung | ✅ erledigt, in Master-DB verifiziert |
| 0.1b / D17 Winebarrel-Epoch-Artefakt (680 Zeilen) | ✅ erledigt (Code + Test + DB-Rebuild verifiziert) |
| 0.2 Historische FX-Tabelle (EODHD) | ✅ erledigt |
| 0.2b TWD fehlt in FX-Fetch | 🟡 Code erledigt — Datenabruf braucht `EODHD_API_TOKEN` (fehlt hier) |
| D16 `fx_rate` für EUR | ✅ erledigt (Code + Test + DB-Rebuild verifiziert) |
| 0.3 `_annotate_fx`/`_apply_fx_rates` | ✅ erledigt — AC revidiert (D18), `fx_status='MISSING'` flaggt 159 749 der 166 480 Lücken-Zeilen explizit (Rest: 6 731 Währung-NULL, bewusst nicht geflaggt, siehe §5) |
| 0.4 / D19 Flaschengrösse klären | ✅ erledigt — `bottle_size_dl` NULL 46,5 %→2,15 % (Rest = echte Mischlose, bewusst nicht defaultet); zacky-Bug (D19) + `_parse_bottle_formats`-Gate-Lücke behoben |
| 0.5 `price_per_bottle_eur` befüllen | ✅ erledigt — AC revidiert (D18-Prinzip); 91,74 % der Zeilen *mit echtem Preis* haben den Wert, Rest erklärt/geflaggt (inkl. neu gefundenem `ZERO_PRICE`) |
| 0.6 / D20 Outlier-/Dubletten-Bereinigung | ✅ erledigt — `DUP_CANDIDATE` 23 636, `OUTLIER` 67 258, `price_kind='COTE'` 33 963 (alle idealwine), nur geflaggt, nichts gelöscht |
| 0.7 View `forecast_input` | ✅ erledigt — 969 183 Zeilen / 119 646 Serien, Zeilenbilanz im Build-Report |
| **Gate G0** (Review Stufe 0) | ✅ erledigt 2026-11-06 — 9 echte Bugs über 2 Runden gefunden+behoben (Wermuth-Spaltenversatz+Trailing-Blank, Magnum/Double-Magnum-Grössenerkennung inkl. Bare-Word-Kollisionen, UNKNOWN-Lose, Outlier-Kontamination, D15-Fenster-Scope, `strip_bottle_format`-Fragmentierung), D21 neu eröffnet. 0.2b bleibt blockiert (Token) |
| Stufe 1 – Baselines & Eval-Harness | ⬜ nicht begonnen, kein `data/forecast/`-Paket im Repo |
| Stufe 2 – Local-Level-Modell (Kalman) | ⬜ nicht begonnen |
| Stufe 3 – Gruppenindex/Fallback | ⬜ nicht begonnen |
| Stufe 4 – Konforme Kalibrierung | ⬜ nicht begonnen |
| Stufe 5 – Serving (API/UI) | ⬜ nicht begonnen |

**Todo-Liste, in Reihenfolge:**

1. ~~D-Entscheide nachholen~~ — **erledigt 2026-11-05**, D12/D15/D16/D17
   entschieden (§6).
2. ~~D16/D17 umsetzen~~ — **erledigt 2026-11-05**, committed + gepusht auf
   `feat/price-forecast-stage0` (PR #105), Senior-Review clean.
3. ~~0.2b — TWD zu `fetch_fx.py` ergänzen~~ — **Code erledigt 2026-11-05**,
   committed. **Blockiert auf einen manuellen Schritt:** jemand mit
   `EODHD_API_TOKEN` muss `python3 data/fetch_fx.py --currencies TWD`
   einmal laufen lassen (nicht in dieser Umgebung möglich), danach Build
   erneut.
4. ~~0.3 — Abdeckungs-AC nachrechnen~~ — **erledigt 2026-11-05.** 96,04 %
   roh, Rest-Lücke zu 95 % strukturell (AUD vor EODHD-Cache-Start
   2006-03-01). **D18 entschieden (§6): AC gesenkt + `fx_status='MISSING'`
   flaggt jede Lücken-Zeile mit bekannter Währung und `lot_date`** — Code
   (Schema-Spalte, CHECK-Constraint, `_apply_fx_rates`-Update, 3 Tests)
   umgesetzt.
5. ~~0.4 — Flaschengrösse klären~~ — **erledigt 2026-11-05.** D19
   (zacky-Bug) behoben, `_parse_bottle_formats`-Gate-Lücke geschlossen,
   Default-Regel (`_assume_default_bottle_size`) umgesetzt, Review-Fix:
   Mischlose (`mixed_lot=1`) bekommen bewusst keinen Default. `NULL`-
   Anteil 46,5 %→2,15 % (Rest = echte Mischlose). Formale
   100-Lose-Stichprobe **nachgeholt in Gate G0** (siehe Punkt 9) —
   fand dabei zwei weitere, unabhängige echte Bugs (Wermuth-sa-
   Spaltenversatz, Magnum/Double-Magnum-Grössenerkennung).
6. ~~0.5 — `price_per_bottle_eur` befüllen~~ — **erledigt 2026-11-05.**
   `_fill_price_per_bottle` umgesetzt, AC revidiert nach D18-Prinzip,
   Review fand + Fix selbst fand je einen weiteren echten Bug (MIXED-
   Lots fälschlich bepreist, `ZERO_PRICE`-Fälle verletzten die „≤0"-AC):
   91,74 % der Zeilen mit echtem Preis haben den Wert, jede Lücke
   erklärt/geflaggt (`fx_missing`→D18, `NO_PREMIUM_POLICY`→winebarrel,
   `ZERO_PRICE`→60k+ ackerwines-Zeilen mit Zuschlag=0, `qty_zero`→
   Datenfehler). Verifiziert: 0 Zeilen mit Preis ≤ 0 in der ganzen DB.
   Formale Los-Konstellationen-Tabelle **nachgeholt in Gate G0**
   (siehe §5, 9 Konstellationen gegen echte Zeilen nachgerechnet).
7. ~~0.6 — Outlier/Dubletten-Bereinigung~~ — **erledigt 2026-11-06.** D20
   (Dubletten-Regel geändert, siehe §6), `price_kind='COTE'` für
   idealwine (D11), robuste z-Score-Ausreisser-Markierung. Alles nur
   geflaggt (`ppb_flags`), nichts gelöscht/zusammengeführt. Zwei
   Review-Runden fanden je einen echten Bug: Runde 1 — `OUTLIER`-Gruppen
   mussten `price_kind='COTE'`-Zeilen ausschliessen (idealwines Cote
   hätte sonst echte Auktionspreise verzerrt); Runde 2 führte selbst
   einen Bug ein (`_flag_cote_prices`/`_flag_duplicate_lots` vor
   `resolve_wines()` verschoben) und behauptete fälschlich, das sei
   gleichwertig — beim Nachbau-Verifizieren selbst entdeckt: die
   verschobene Reihenfolge liess `_fill_price_per_bottle`s eigenes
   (nicht-additives) `UPDATE ... ppb_flags=?` die gerade gesetzten
   `DUP_CANDIDATE`-Flags wieder überschreiben (23 636→14 395 Zeilen,
   grösstenteils sylvies betroffen). Fix: `_flag_duplicate_lots` läuft
   jetzt nach `_fill_price_per_bottle`, mit eigenem Regressionstest.
   Finale, am Rebuild verifizierte Zahlen: `DUP_CANDIDATE` 23 636
   (identisch mit der `_check_duplicate_lot_numbers`-Gate-Prüfung),
   `OUTLIER` 73 604 (Stand 2026-11-06, vor Gate G0), `price_kind='COTE'`
   33 963. Die 127 restlichen `1,0 dl`-Zeilen (0.4) und die 20 965-/
   23 709-Dichtezahlen aus §2.10 wurden **nicht** im Rahmen von 0.6 neu
   bewertet — nachgeholt in Gate G0, siehe Punkt 9. **`OUTLIER` ändert
   sich im Rahmen von Gate G0 nochmal auf 67 258** (zwei weitere, von
   der Code-Review gefundene Bugs behoben: Vergleichsgruppen mischten
   bisher Zeilen mit unzuverlässigem `vintage_status` und `QTY_SUSPECT`-
   Zeilen ein — siehe Gate-G0-Abschnitt).
8. ~~0.7 — View `forecast_input`~~ — **erledigt 2026-11-06.** Baut auf
   `single_wine_prices` auf (SINGLE, `wine_ref_id` aufgelöst,
   `vintage_status` sauber), dazu D14 (`sold = 1`, **nicht** die alte
   Spec-Formulierung `sold IS NOT 0` — die hätte `sold IS NULL` fälschlich
   miteingeschlossen, da `NULL IS NOT 0` in SQL wahr ist), `lot_date
   IS NOT NULL`, D11 (`price_kind IS NULL`, aktuell deckungsgleich mit
   `sold=1` — alle 33 963 COTE-Zeilen haben `sold≠1` — aber bewusst
   explizit gehalten, da das eine Zufallskorrelation der Daten ist,
   keine Schema-Garantie), die 0.6-Flags (`OUTLIER`/`QTY_SUSPECT`/
   `DUP_CANDIDATE`, `instr()`-Substring-Suche statt `LIKE`, gleiche
   `_`-Falle wie bei `_report_06_flags`) und D15 (pro Serie
   `wine_ref_id·vintage·size_class` per Fenster-Funktion `MAX(lot_date)
   OVER (PARTITION BY ...)`, ausgewertet gegen `date('now', '-36
   months')` zur Abfragezeit, nicht zum Build-Zeitpunkt — eine Serie
   fällt mit der Zeit von selbst aus `forecast_input`, ohne Rebuild).
   `size_class` = `bottle_size_dl` direkt (D10: eigene Serien pro
   Grösse, kein Äquivalenzfaktor). 14 neue Tests. AC (`_report_07_
   forecast_input`, im Build-Report), Stand 2026-11-06 vor Gate G0:
   Zeilenbilanz 4 297 347 → 966 347 Zeilen (118 681 Serien). **Nach
   Gate G0** (Wermuth-sa-Spaltenversatz, Magnum-Grössenerkennung,
   `_flag_price_outliers`-Kontamination und der D15-Fenster-Scope-Bug
   alle behoben, 15 neue Tests): **4 297 347 → 969 183 Zeilen
   (119 646 Serien)** — `single_wine_prices` 3 234 509 (-1 062 838),
   `sold=1` 1 413 299 (-1 821 210), `lot_date` 1 411 711 (-1 588),
   `price_per_bottle_eur` 1 348 894 (-62 817), `price_kind` 1 348 894
   (-0, s. o.), 0.6-Flags 1 268 653 (-80 241), D15-Serie-aktiv 969 183
   (-299 882), davon 82 956 Zeilen (8,6 %) `size_assumed=1` (D21, offen,
   siehe §6). Summen stimmen (letzte Stufe = direkte
   `SELECT COUNT(*) FROM forecast_input`).
9. ~~**Gate G0**~~ — **erledigt 2026-11-06.** Senior-Review aller
   Stufe-0-Schritte (mechanischer Review `/code-review high` auf dem
   ganzen Branch-Diff gegen `master`, Multi-Agent, 2 Review-Runden inkl.
   Straggler-Fund). Alle angekündigten Lücken abgearbeitet: 0.1b/D17
   bereits erledigt (nur bestätigt), 0.3-AC bereits revidiert (nur
   bestätigt), 0.4/0.5/0.6 formale Stichproben nachgeholt (siehe dort),
   127 restliche `1,0 dl`-Zeilen vollständig aufgeklärt (64 echter Bug,
   behoben; 63 echte Mini-Formate, kein Bug), §2.10-Dichtezahlen neu
   gemessen (Punkt 10b). **0.2b bleibt offen** — reiner Datenabruf-
   Blocker (`EODHD_API_TOKEN` fehlt in dieser Umgebung), kein Code- oder
   Review-Befund, siehe eigener Eintrag oben.

   **Drei echte, bis dahin unentdeckte Bugs gefunden und behoben** (alle
   mit neuen Tests, dreifacher bzw. vierfacher Master-DB-Rebuild
   verifiziert):
   1. **`load_wermuth_validated`'s Spalten-Erkennung** (0.4-Stichprobe):
      215 Zeilen mit falschem Jahrgang/Menge/Flaschengrösse **und
      falschem Zuschlagspreis** (siehe 0.4-Abschnitt für Details).
   2. **`parse_bottle_format`'s Compound-/Bare-Word-Lücke**: bindestrich-
      getrennte ("Double-Magnum") und zahllose ("... Magnum" ohne
      führende Zahl) Formatangaben wurden nie erkannt — betraf
      dorotheum/besch-cannes systematisch und halbierte
      `price_per_bottle_eur` für jeden solchen Fall (siehe 0.4-Abschnitt).
   3. **`lot_kind='UNKNOWN'` bekam einen fingierten Flaschenpreis**
      (`_assume_default_bottle_size`/`_fill_price_per_bottle` prüften nur
      `<> 'MIXED'`, nicht `= 'SINGLE'`) — 357 072 Zeilen (Spirituosen oder
      Lose ganz ohne Wein-Namen) hatten einen unmarkierten, bedeutungslosen
      Flaschenpreis. Neue Flags `UNKNOWN_LOT`.

   **Zwei weitere Bugs aus dem mechanischen Code-Review gefunden und
   behoben** (nicht aus der Stichprobe, sondern aus systematischer
   Diff-Analyse):
   4. **`_flag_price_outliers`'s Vergleichsgruppen-Kontamination**: las
      aus `lots` statt `single_wine_prices` und nutzte
      `COALESCE(vintage_final, vintage)` statt nur `vintage_final` —
      Zeilen mit unzuverlässigem `vintage_status` (NV/MV/MISSING/
      AMBIGUOUS/CONFLICT/INVALID) konnten eine Vergleichsgruppe über
      ihre rohe, ungeprüfte `vintage`-Spalte verzerren. `QTY_SUSPECT`-
      Zeilen waren ebenfalls nicht ausgeschlossen (nur `COTE` war es).
      Fix: liest jetzt aus `single_wine_prices`, gruppiert auf
      `vintage_final`, schliesst `QTY_SUSPECT` wie `COTE` aus.
      `OUTLIER` 73 604 → final 67 258 Zeilen (nach allen G0-Fixes).
   5. **`forecast_input`s D15-Fenster-Funktion sah nur bereits gefilterte
      Zeilen** — `MAX(lot_date) OVER (...)` stand in derselben Subquery,
      deren `WHERE` schon die 0.6-Flags ausschloss, sodass eine Serie mit
      genau einer jüngeren, aber geflaggten Beobachtung fälschlich als
      "inaktiv" galt und komplett (inkl. sonst gültiger älterer Zeilen)
      aus `forecast_input` fiel. Fix (nach einer weiteren Review-Runde
      auf eine `WITH eligible AS (...)`-CTE vereinfacht statt eines
      zweiten Joins, um die Basis-Filterbedingung nicht doppelt zu
      pflegen): Fenster-Funktion läuft jetzt in einem einzigen Pass über
      ungefilterte, aber sold/Preis/Datum-berechtigte Zeilen; Flag-
      Ausschluss und 36-Monate-Check kommen erst danach, zusammen.
      `forecast_input` 966 347 → final 969 183 Zeilen.
   6.–9. **Vier weitere echte Bugs, gefunden beim Re-Review der
      eigenen G0-Fixes selbst** (zweite Mechanik-Review-Runde direkt auf
      den unkommitteten Änderungen): drei bare-word-Formatkollisionen in
      `parse_bottle_format`s neuem Bare-Word-Fallback (DEMI/HALF/
      BALTHAZAR/MELCHIOR/DM lasen echte Markennamen/Fliesstext als
      Flaschenformat — behoben durch ein kuratiertes, live gegen die
      Archivdaten geprüftes Allow-List), eine Präzedenz-Lücke (ein
      schwacher Bare-Word-Treffer in `name` blockierte einen starken,
      expliziten Treffer in `description`), ein Trailing-Blank-Zähl-Bug
      in `load_wermuth_validated` (ein leeres CSV-Endfeld wurde als
      echte 11. Spalte mitgezählt, 2 weitere falsch gelesene Zeilen),
      und `strip_bottle_format` wandte die Compound-Normalisierung nie
      an (liess "Double-Magnum"-Text im Weinnamen stehen, fragmentierte
      Wein-Identitäten). Alle mit Tests, siehe §8 Review-Log für die
      vollständige Aufschlüsselung über beide G0-Runden.

   Drei weitere Review-Befunde **bewusst nicht gefixt, sondern
   dokumentiert/vertagt** (kein aktiver Schaden nachgewiesen, Aufwand/
   Risiko einer Änderung überwiegt den Nutzen):
   - `fx_status='MISSING'` prüft nicht, ob die Währung überhaupt bekannt
     ist (nur hypothetisch — aktuell 0 betroffene Zeilen).
   - `zacky_bottle_size_dl`s Bare-Zahl-Erkennung lebt am Call-Site statt
     in `parse_dl` selbst (D19 bleibt behoben, nur die Architektur wäre
     verbesserbar).
   - `_winebarrel_date`s 1970-Epoch-Fix ist winebarrel-spezifisch statt
     generisch in `parse_date` (bestätigt: aktuell 0 Zeilen mit
     `lot_date='1970-01-01'` irgendwo sonst in der DB — rein
     vorsorglich).
   Reuse/Duplikat-Befunde (Flag-Ausschluss-Liste dreifach, `_flag_
   duplicate_lots`/`_check_duplicate_lot_numbers`-Logik doppelt) **wie
   in den vorherigen Runden als akzeptiertes Tech-Debt eingestuft** —
   kein Korrektheits-Bug, nur Pflegeaufwand bei künftigen Änderungen.
   `generate_review_csv.py` (ein von der Review gefundenes, nicht von
   diesem PR berührtes Nachbar-Skript) bekam zusätzlich die Spalte
   `size_assumed`, da `_assume_default_bottle_size` (0.4) sein `MAX(
   bottle_size_dl)` sonst unmarkiert mit einem echten Wert vermischt.
   **D21 neu eröffnet** (siehe §6): `size_assumed=1`-Zeilen bleiben in
   `forecast_input`, nur gezählt (8,6 % davon betroffen), nicht
   ausgeschlossen — Produktentscheidung, nicht Teil von G0.
10. Erst danach Stufe 1 (Paket-Gerüst `data/forecast/`, `statsmodels` in
    `requirements.txt`, Baselines, Rolling-Origin-Evaluator) — siehe §5,
    unverändert seit 2026-10-29, noch nichts davon existiert im Repo.

**Reihenfolge-Begründung:** 0.4/0.5 sind der grösste Hebel laut eigenem
Risiko-Ranking (§1) — ohne `price_per_bottle_eur` ist jede spätere Stufe
(1–5) Scheingenauigkeit auf einer nicht normalisierten Zielgrösse. 0.2b/0.3
sind klein und schnell erledigt, aber **vor** G0 nötig, weil G0 explizit
„Stimmen Flaschenpreise/FX stichprobenartig?" prüft (§7).

---

## 2. Established Facts (live gegen Master-DB verifiziert, 2026-10-29)

Quelle: `/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite`, View
`single_wine_prices` (lot_kind=SINGLE, wine_ref_id gesetzt, Jahrgang bekannt).

1. **2 142 298** Zeilen, 136 207 verschiedene `wine_ref_id`, Zeitraum bis
   2026-08-18; jüngste Jahre: 2022 136 k, 2023 131 k, 2024 105 k, 2025 134 k,
   2026 (bis Aug) 78 k Lose.
2. **`price_per_bottle` = NULL in 100 %** der Zeilen. Spalte existiert, wird nie
   befüllt.
3. **`bottle_size_dl`**: 1 931 006 NULL (90 %); 7,5 dl nur 103 233; 15 dl
   (Magnum) 16 295; 1,0 dl 21 353 (Verdacht: Einheitenfehler/Magnum-Schreibweise).
4. **`quantity`** gesetzt bei 1 562 738; `quantity>1` bei 807 233 → Los-Preis ≠
   Flaschenpreis. Division nötig, sonst Faktor-n-Fehler.
5. **`sold`**: NULL 1 323 821 (62 %), 1 = 694 716, 0 = 123 761. NULL-Semantik
   ungeklärt (Haus-abhängig?) → muss je Haus geklärt werden.
6. **Währungen**: AUD 1 278 203 (langtons, 60 %!), USD 226 k, GBP 216 k,
   EUR 211 k, CHF 95 k, HKD 79 k. **`fx_rate` nur bei 4 854 Zeilen** (NLG).
   Es existiert **keine** historische FX-Tabelle für die Modernwährungen.
7. **`lot_date`**: 2 133 924 ISO, **119 im Format `dd.mm.yyyy`**, 8 255 NULL.
   String-Min/Max sind dadurch unbrauchbar.
8. **Haus-Mix**: langtons 1,28 Mio, christies 490 k, zacky 84 k,
   winefields 69 k, sothebys 58 k, wermuth-sa 52 k, besch-cannes 47 k,
   idealwine 34 k. Langtons (AUD, Australien) dominiert → Gefahr, dass „der
   Markt" faktisch „Australien" ist.
9. **Preisbasis heterogen** (`docs/premium-policy.md`): Hammer vs. Brutto,
   Premium 10–27,6 %, Lotgebühren, MwSt unterschiedlich. Spalten `hammer_price`
   (2 009 610), `realised_price` (2 018 146), `total_price`, `price_source`
   (OBSERVED/DERIVED).
10. **Dichte (Wein·Jahrgang, ISO-datiert, sold≠0, Preis>0):** 245 755 Gruppen;
    ≥ 5 Lose: 55 443; ≥ 10: 28 886; ≥ 20: 14 403; ≥ 50: 5 727;
    ≥ 10 Lose über ≥ 3 Jahre: 23 709; ≥ 8 verschiedene Auktionen: 20 965.
    ⇒ Rund **15–25 k** Gruppen sind für Stufe 2 realistisch; ~230 k
    brauchen den Fallback oder `INSUFFICIENT_DATA`. **(Veraltet — diese
    Zahlen nutzten `sold≠0`, nicht D14s `sold=1`; neu gemessen in
    Gate G0, siehe Punkt 10b.)**
10b. **Dichte neu gemessen gegen `forecast_input` (Gate G0, 2026-11-06,
    inkl. `wine_ref_id·vintage·size_class` als Serienschlüssel statt nur
    Wein·Jahrgang, D14 `sold=1` statt `sold≠0`, plus alle 0.5/0.6-Filter
    und D15s 36-Monate-Aktivitätsfenster):** 119 646 Serien insgesamt;
    ≥ 5 Lose: 30 760; ≥ 10: 17 409; ≥ 20: 9 135; ≥ 50: 3 407;
    ≥ 10 Lose über ≥ 3 Jahre: 16 846; ≥ 8 verschiedene Auktionen: 17 847.
    Rund **halb so viele** Serien wie die alte (vor-D14) Schätzung in
    jeder Schwelle — plausibel und erwartet (D14 selbst sagte "~62 % der
    Zeilen entfallen" voraus), kein neuer Befund. ⇒ Die Stufe-2-Schätzung
    aus Punkt 10 ("15–25 k Gruppen realistisch") bleibt **ungefähr
    gültig**, eher am unteren Rand (≥ 10 Lose: 17 409 Serien).
11. `statsmodels`/`numpy`/`pandas` sind in der lokalen Python-Umgebung nicht
    installiert.
12. Reihenfolge der Annotation in `build_db.py`: `_annotate_fx` →
    `_apply_premium_policy` → `_apply_tax` → `_fill_lot_date`. Neue Spalten
    gehören dort hinein (atomarer Build: tmp + `os.replace`).

---

## 3. Entscheidungen (D-Nummern, im Review festzuzurren)

| # | Entscheidung | Empfehlung | Begründung |
|---|---|---|---|
| D1 | Zielgrösse | **Brutto-Zuschlag inkl. Premium, ohne MwSt, je 0,75 l, in EUR** (`realised_price`/qty/Flaschenäquivalent) | Vergleichbar über Häuser; entspricht „was der Käufer für den Wein bezahlt". Alternative Hammer-netto nur Häuser mit Hammer – verworfen (Gross-only-Häuser fehlen sonst). |
| D2 | Zielvariable | `y = ln(Preis je 0,75 l EUR)` | Rechtsschiefe, multiplikatives Rauschen (Hinweis aus Brief) |
| D3 | Prognosehorizont | **nächste Auktionsbeobachtung** und **+12 Monate** | „nächster Preis" ist unregelmässig; 12 M ist produktrelevant |
| D4 | Intervalle | 50 / 80 / 95 % | 80 % ist Standardanzeige |
| D5 | Mindestdichte Stufe 2 | ≥ 10 Beobachtungen, ≥ 3 Kalenderjahre, ≥ 5 Auktionen, letzte Beobachtung ≤ 36 M alt | Datenbasiert (§2.10) – im Schritt 2.1 über Backtest zu kalibrieren, nicht zu raten |
| D6 | Fallback | Gruppenindex-Prognose, Intervall aus Gruppenstreuung, Flag `method=GROUP_INDEX` | Brief: „breiteres Intervall statt Scheingenauigkeit" |
| D7 | Zensur (`sold=0`) | v1: ignorieren, aber **als bekannte Verzerrung dokumentieren** und Rückgangsquote je Gruppe mitliefern | Tobit-Modell wäre Overkill für v1 |
| D8 | Haus-/Los-Effekte | Als **Fixed Effects** vorab herausrechnen (Stufe 1.3), Rest geht ins Kalman-Modell | Brief: Auktionsrauschen separat |
| D9 | Code-Ort | `data/forecast/` als Paket, Output in neue DB-Tabelle `price_forecasts` (nicht in `lots`) | Prognose ist abgeleitet, regenerierbar, versioniert |

---

## 4. Guardrails (gelten für ALLE Stufen)

**G1 – Zeitliches Splitten.** Evaluation ausschliesslich *Rolling-Origin*:
Modell sieht nur Daten `< t`, prognostiziert Beobachtungen `≥ t`. Zufalls-
Splits sind verboten. Test: `test_no_lookahead` baut künstlich eine Serie, bei
der das Zukunftsdatum den Wert verrät; das Modell darf davon nicht profitieren.

**G2 – Messlatte.** Ein Modell darf nur live, wenn es auf dem Holdout
(letzte 24 Monate, Rolling-Origin) die Baselines schlägt bei
**(a) Pinball-Loss/CRPS (Median-Fehler: MAPE auf EUR)** *und*
**(b) Intervall-Coverage innerhalb ±3 Prozentpunkte** der Nominalabdeckung
(80 %-Intervall deckt 77–83 % der Realisierungen).

**G3 – Kein stilles Raten.** Jede Prognose trägt `method`, `n_obs`, `last_obs_date`,
`data_quality_flags`. Wenn D5 nicht erfüllt: `INSUFFICIENT_DATA`, kein Wert.
Test: Property-Test, dass keine Zeile mit `n_obs < min` einen Punktwert hat.

**G4 – Plausibilität.** Harte Checks pro Lauf (Abbruch bei Verletzung):
Quantile monoton (q10<q50<q90); Intervallbreite wächst mit Horizont;
Median innerhalb [0,2×; 5×] des letzten Medians (sonst Flag `EXTRAPOLATION`,
kein Abbruch); keine NaN/Inf; Zeilenzahl-Bilanz
(`forecast + insufficient = candidates`).

**G5 – Determinismus.** Fester Seed, sortierte Eingaben, `numpy`/`statsmodels`-
Versionen gepinnt; Test analog `test_repeatability.py`: zwei Läufe → identische
Tabellen (Hash-Vergleich).

**G6 – Read-only auf der Master-DB.** Modelle lesen aus der DB (`mode=ro`),
schreiben nur in `price_forecasts` einer separaten Datei bzw. nach dem
atomaren Build-Muster (tmp + `os.replace`). Backup vor jedem Schema-Change
(`.bak-<tag>` wie bisher).

**G7 – Gold-Set.** 20–30 handverlesene Weine (Mix: Bordeaux 1er Cru, Burgund,
Penfolds Grange, Barolo, dünn besetzt) mit manuell geprüfter Historie
(`data/tests/fixtures/forecast_gold.json`). Erwartung: Prognose plausibel,
visuell geprüft (Plot-Review durch Fachperson), Regressionstest ab Freigabe.

**G8 – Definition of Done je Schritt.** Jeder Micro-Step in §5 hat:
(1) ausführbares Abnahmekriterium (Befehl + erwartete Ausgabe),
(2) Test(s) grün (`pytest data/tests -q`), bestehende Tests unverändert grün,
(3) Eintrag im Review-Log (§7).

---

## 5. Micro-Steps

Notation: **Aufwand** S ≤ 2 h, M ≤ ½ Tag, L ≤ 1,5 Tage. **AC** = Abnahmekriterium.

### Stufe 0 – Daten-Grundlage (Voraussetzung)

Jeder Schritt ändert `build_db.py` isoliert, mit eigenem Commit + Test.

**0.1 Datumsbereinigung** (S)
- `lot_date` normalisieren: `dd.mm.yyyy` → ISO in `_fill_lot_date`; Rest (NULL)
  per `auction_date` füllen (existiert), Rest bleibt NULL + Zähler in `build_metrics`.
- AC: `select count(*) from lots where lot_date not like '____-__-__%' and lot_date is not null` = 0.
- Test: `data/tests/test_lot_date.py` (Format-Matrix inkl. 29.02., 1.1.1900, ungültig, Idempotenz).
- **Status: erledigt 2026-10-29**, in der Master-DB verifiziert 2026-11-05
  (`_normalize_lot_date` in `build_db.py`, vor `_fill_lot_date`): 4 203 026
  Zeilen ISO, 0 Nicht-ISO, 94 321 NULL (unverändert erwartet, Häuser ohne
  Datum).
- **Neuer Befund 0.1b, entschieden 2026-11-05 (D17), Code-Fix ausstehend:**
  680 Lose (winebarrel) haben `lot_date = 1970-01-01` — bestätigt ein
  Rohdaten-Artefakt (`auction_end: "1970-01-01 01:00:00"` steht so im
  Archiv, kein zweites Datumsfeld im Lot, `auction_date` der virtuellen
  "all"-Auktion ist selbst NULL, also kein Backfill möglich). D17:
  `lot_date` auf NULL setzen. Betrifft `forecast_input` ohnehin nicht
  (alle 680 Zeilen haben `sold IS NULL` → D14 filtert sie schon raus) —
  der Fix ist nur für andere Konsumenten von `lot_date` relevant (GUI
  o.ä.), damit nirgends "1970" als echtes Datum erscheint.

**0.2 Historische FX-Tabelle** (M)
- Neue Tabelle `fx_rates(date, currency, per_eur)`; Quelle: **EODHD** (EOD-Forex, Paare `<CCY>EUR.FOREX`; Tagesschlusskurse, Monatsmittel werden abgeleitet). Abruf-Skript `data/fetch_fx.py` liest den Key aus `EODHD_API_TOKEN`, cached Rohantworten im Archiv (Samsung), ist idempotent; Test mit gemockter HTTP-Antwort, kein Netz in CI. Abdeckung der Historie je Währung vorab prüfen (Start der Zeitreihe; Pre-Euro-Währungen). Für Zeiträume vor 1999: Fallback auf ein dokumentiertes Verfahren oder Ausschluss (`fx_missing`).
- Quelle **im Dokument festhalten** (URL, Abrufdatum, Lizenz). Das Skript ist idempotent und lädt keine Daten ohne explizite Aktion.
- AC: für alle (currency, Monat) der Lose existiert ein Kurs, ausser Währungen mit Flag; Bericht der Lücken.
- Test: Stichproben-Kurse gegen publizierte Werte (3 Datenpunkte als Fixture).
- **Status: erledigt** (genaues Datum nicht im Log, vor 2026-11-05 verifiziert;
  `data/fetch_fx.py` + `fx_rates`-Tabelle + `_load_fx_rates` existieren und
  sind getestet, `data/tests/test_fx_rates.py`). EODHD-Cache liegt unter
  `/Volumes/samsung/winefeed-data/fx/` für `AUD, USD, GBP, CHF, HKD, SGD,
  CNY` (je ein `EUR<CCY>.json`, 1998→heute).
- **Quelle/Abrufdatum/Lizenz (nachgetragen Gate G0, 2026-11-06, aus den
  Cache-Dateien selbst ausgelesen, `d['fetched_at']`/`d['ticker']` je
  `EUR<CCY>.json`):** API **EODHD** (eodhd.com), Endpoint `/api/eod/`,
  Ticker `EUR<CCY>.FOREX`, Tagesschlusskurs. Alle sieben aktuell
  gecachten Währungen am **2026-11-01** abgerufen: AUD (ab 2006-03-01,
  5 393 Tage), CHF/GBP/SGD/USD (je ab 1998-01-02, ~7 59x Tage), CNY (ab
  2002-01-02, 7 282 Tage), HKD (ab 1999-12-31, 7 995 Tage), jeweils bis
  2026-10-30/31. **Lizenz:** bestehendes EODHD-Abo (D13); laut
  `eodhd.com/financial-apis/terms-conditions` bzw.
  `.../commercial-vs-personal-license-use` ist lokales Speichern der
  Daten während der aktiven Abo-Laufzeit zulässig, Weitergabe/
  Redistribution an Dritte dagegen nicht ohne gesonderte Vereinbarung —
  für diesen Anwendungsfall unkritisch: der Cache liegt nur lokal auf
  der Samsung-Disk, es werden nur abgeleitete `fx_rate`-Werte in die
  Master-DB geschrieben, keine Rohdaten publiziert oder weitergegeben.
- **Befund 0.2b (neu, 2026-11-05): `TWD` fehlt in `fetch_fx.py`'s
  `CURRENCIES`-Liste**, obwohl 568 Lose in `TWD` fakturiert sind — diese
  bleiben ohne `fx_rate`, bis die Liste ergänzt und `fetch_fx.py` erneut
  gegen die API gelaufen ist. Kleiner, klar umrissener Nachtrag, siehe
  Todo unten.

**0.3 `_annotate_fx` erweitern** (M)
- `fx_rate` (Einheiten je 1 EUR) und `fx_target_currency='EUR'` für *alle* Währungen via Lotdatum-Monat; Zeilen ohne Kurs: `fx_rate` NULL + `fx_status='MISSING'`.
- AC (revidiert 2026-11-05, D18): ~~`fx_rate`-Abdeckung ≥ 99 % der Zeilen
  mit Datum~~ — **jede Zeile mit `lot_date` und bekannter Währung hat
  entweder `fx_rate` oder `fx_status='MISSING'`; keine unerklärte, unmarkierte
  Lücke.** NLG-Bestand unverändert (Regression: Hash der 4 854 NLG-Zeilen
  vor/nach identisch).
- **Status: erledigt 2026-11-05.** Nach D16 (EUR-Fix) + D17
  (winebarrel-NULL) + 0.2b (Code, TWD-Cache-Daten noch nicht abgerufen)
  neu gebaut, mit dem richtigen Nenner (`lot_date IS NOT NULL` =
  4 202 346 Zeilen) gerechnet: **4 035 866 mit `fx_rate` = 96,04 %**, Rest
  (166 480 Zeilen) vollständig aufgeschlüsselt; davon 159 749 laut D18
  geflaggt (`fx_status='MISSING'`, neue Spalte + CHECK-Constraint), die
  übrigen 6 731 (Währung NULL) bewusst nicht:
  - **AUD 158 920 (95 % der Lücke)** — alle vor dem Start der EODHD-AUD-
    Reihe (2006-03-01); langtons hat AUD-Lose seit den 1990ern (bereits
    in §2.8 als Risiko vermerkt). Strukturelle Lücke, nicht durch
    Nachfetchen lösbar.
  - **HKD 261** — alle 1999, vor Start der EODHD-HKD-Reihe (1999-12-31).
  - **TWD 568** — reiner Daten-Nachtrag, Code ist fertig (0.2b), fehlt nur
    der API-Call (kein `EODHD_API_TOKEN` in dieser Umgebung); bekommt
    ebenfalls `fx_status='MISSING'`, bis die Cache-Daten da sind.
  - **Währung NULL 6 731 — bewusst NICHT geflaggt**, da kein FX-Problem,
    sondern eine Vorstufe: winebarrel's statischer Dump setzt `currency`
    überhaupt nicht (6 695 Zeilen, Loader-Lücke seit jeher, nicht Teil
    dieser Session); christies 36 Einzelfälle. Separat zu klären.
  - USD/GBP/CHF/SGD/CNY: **0 Lücken** — vollständig abgedeckt seit
    Cache-Start 1998.
  NLG-Regressionstest (4 854 Zeilen unverändert) nicht erneut verifiziert
  seit dem ackerwines-Fix — ausstehend.

**0.4 Flaschengrösse klären** (M)
- Untersuchung: Welche Häuser liefern `bottle_size_dl`? Wo steht Info in `description`/`raw_wine` („Magnum", „1.5L", „75cl", „Jeroboam")? Einheit `1.0` (21 k Zeilen) prüfen: vermutlich Liter statt dl.
- Output: Entscheidungstabelle + Parser-Erweiterung in `data/wine_resolution/bottle.py` (existiert, ist aktuell modifiziert → vorher `git diff` lesen, nicht überschreiben).
- Default-Regel: `NULL` → 7,5 dl **nur** mit Flag `size_assumed=1`; Magnum etc. werden als eigene Serie geführt oder per Äquivalent-Faktor normiert (Entscheidung D10, siehe §6 offene Punkte).
- AC (erweitert 2026-11-05): `NULL`-Anteil < 10 % oder je Haus begründet
  → **erreicht: 2,15 %** (92 221 / 4 297 347 — final verifiziert, nach
  allen Review-Fixes, siehe Status). Stichprobe/Fehlerquote noch nicht
  formal durchgeführt (siehe Todo vor Gate G0).
- **Status: erledigt 2026-11-05** (final gegen die Master-DB
  nachgebaut und verifiziert, inkl. zwei Review-Fix-Runden). Vier
  Befunde/Fixes:
  1. **D19: zacky's `1.0 dl`-Bug.** 24 129 von 24 256 verdächtigen
     „1,0 dl"-Zeilen waren zacky (99,5 %); `parse_dl` bekam zacky's
     `quantity`-Feld (ein Flaschen-*Zähler*, z. B. literal `"1"`,
     `"6"`, `"12"`) übergeben und interpretierte die blanke Zahl über
     seinen Zahlen-Fallback (gedacht für *andere* Aufrufer wie
     dorotheum's dediziertes `size`-Feld) fälschlich als direkten
     dl-Wert — "1 Flasche" wurde zu "0,1 Liter". Fix:
     `zacky_bottle_size_dl` prüft zuerst, ob der Text nur eine blanke
     Zahl ist (→ `None`), bevor er an `parse_dl` weiterreicht
     (Review-Härtung: Regex deckt auch Dezimalformen wie „6.0" ab, nicht
     nur reine Ganzzahl-Strings). Restliche `1,0 dl`-Zeilen: 127 (andere
     Häuser, nicht untersucht, Kandidat für 0.6).
  2. **`_parse_bottle_formats`-Gate-Lücke** (`build_wines.py`):
     `bottle_size_dl` wurde nur geschrieben, wenn `quantity` *ebenfalls*
     noch NULL war — die meisten Häuser setzen `quantity` aber schon
     beim Laden (oft `1`), sodass dieser Pfad für sie nie feuerte.
     Bestätigt an langtons: 13 155 Lose haben einen
     `parse_bottle_format`-erkennbaren Hinweis im eigenen `wine`-Text
     (z. B. „2 Magnum Set"), der bisher ungenutzt blieb. Fix:
     `bottle_size_dl` aktualisiert jetzt unabhängig davon, ob `quantity`
     schon gesetzt ist; `quantity` bleibt beim konservativeren Gate.
  3. **Default-Regel umgesetzt** (`_assume_default_bottle_size`): jede
     verbleibende NULL-Zeile → 7,5 dl + `size_assumed=1`.
  4. **Review-Fix: Mischlose dürfen keinen fingierten Default
     bekommen.** `_assume_default_bottle_size` lief ursprünglich *vor*
     `_classify_lots` und prüfte nur den rohen Provider-`mixed_lot`-Flag
     — die zusätzlichen Lose, die `_classify_lots` erst über Keyword-/
     Gruppen-Evidenz als `MIXED` erkennt, bekamen trotzdem einen
     fingierten 7,5-dl-Default + `size_assumed=1` (mehrere verschiedene
     Weine/Grössen in einem Los haben keine einzelne sinnvolle Grösse).
     Fix: `run()` ruft jetzt `_classify_lots` vor
     `_assume_default_bottle_size` auf; Letztere prüft `lot_kind <>
     'MIXED'` statt des rohen Flags.
  **Finales Live-Ergebnis** (nach allen Fixes, Master-DB neu gebaut):
  `bottle_size_dl` NULL: **92 221 / 4 297 347 (2,15 %)** — ausschliesslich
  `lot_kind='MIXED'`-Zeilen (verifiziert: 0 NULL-Zeilen ausserhalb von
  MIXED), bewusst nicht defaultet. `size_assumed=1` bei Nicht-MIXED-Zeilen
  korrekt 0 für MIXED (verifiziert). Verteilung der echten/erkannten
  Werte: überwiegend 7,5 dl, dann 15 dl (Magnum), 3,75 dl (Halbflasche),
  30 dl (Doppelmagnum), kleinere Stückzahlen (inkl. ein echter
  11-Liter-Fall bei langtons, „PENFOLDS 3240B - 11L ex Tempe").
- **Gate-G0-Stichprobe (2026-11-06), 127 restliche „1,0 dl"-Zeilen
  (wermuth-sa 64, ackerwines 48, sylvies 13, bestwineauctions 2) gegen
  die Originalquelle geprüft — echter Bug gefunden und behoben:**
  1. **Echter Bug: `load_wermuth_validated`'s Spalten-Erkennung.** Die
     64 wermuth-sa-Zeilen waren KEIN Flaschengrössen-Problem, sondern
     ein Spalten-Versatz-Bug, der auch `hammer_price` selbst verfälscht
     hat (nicht nur `bottle_size_dl`). Die CSV-Dateien
     (`output_WermuthSA_*.csv`, 10 oder 11 Spalten) haben **drei**
     reale Spalten-Layouts, nicht zwei: (a) 10 Spalten ohne Origin,
     (b) 11 Spalten mit Origin an Index 2 (Index 3 dann "null"), (c) 11
     Spalten mit Origin **leer** an Index 2 und einem echten Region-Wert
     an Index 3 (z. B. „Pomerol"). Die alte Erkennung
     (`row[2]` nicht leer ⇒ 11-Spalten-Layout) erkannte (c) fälschlich
     als 10-Spalten-Zeile und verschob Jahrgang/Menge/Flaschengrösse
     **und den Zuschlagspreis** um eine Spalte (verifiziert an Los 28,
     09.09.2017: `hammer_price` wurde als 3600 — dem `estimate_high`-Feld
     — statt der echten 1700 gelesen). Live gezählt: **215 betroffene
     Zeilen** (nicht nur die 64 „1,0 dl"-Fälle — 145 weitere hatten eine
     unauffällige, aber ebenso falsche Flaschengrösse/Preis). Fix: Offset
     richtet sich nur noch nach der Spalten-**Anzahl** (`len(row) >= 11`),
     nicht nach dem Inhalt von Spalte 2 — 5 neue Tests
     (`WermuthValidatedCsvColumnShiftTest`, alle vier Spalten-Varianten
     abgedeckt). Nach Rebuild: wermuth-sa hat 0 Zeilen mit
     `bottle_size_dl=1,0` mehr; Los 28 jetzt korrekt (Jahrgang 2009,
     Menge 12, 7,5 dl, `hammer_price=1700`).
  2. **Restliche 63 Zeilen: keine Bugs, echte Mini-Formate.** Gegen die
     Rohdaten geprüft (JSON direkt gelesen): ackerwines' „Tokay/Tokaji
     Essencia/Eszencia" (`bottle_size_raw: "100 ml"` im Rohdatensatz —
     Tokaji Eszencia wird real in 100-ml-Flaschen abgefüllt), Whisky-/
     Cognac-/Rum-Miniaturen (z. B. „Macallan ... Miniature Box Set",
     „6abv71%, 1x6 100ml ocb" — Rohtext nennt „100ml" explizit),
     bestwineauctions' „PARA VINTAGE TAWNY 1910" (Rohfeld bereits
     `bottle_size_dl: 1.0`, Los-Titel „0,100 Liter Bottle" — ein reales
     100-ml-Sammlerformat von Seppeltsfield), sylvies' „Aceto Balsamico
     Tradizionale di Modena" und „Elixir Vegetal de la Grande
     Chartreuse" (traditionelle 100-ml-Kleinflaschen). **Bekannte,
     nicht behobene Randnotiz:** einige dieser Positionen sind gar kein
     Wein (Whisky, Rum, Balsamico-Essig) und erhalten teils trotzdem
     einen `wine_ref_id` (20 ackerwines-, 4 sylvies-Zeilen laufen durch
     bis `vintage_status='STRUCTURED'`) — harmlos für andere Weinserien
     (eigener, korrekt benannter `wine_ref_id`), aber ein pre-existing
     Scope-Problem der Ingestion (nicht Teil von 0.4/dieser Session,
     separat zu klären). Die 100-Lose-Stichprobe ist damit für alle 127
     ursprünglich verdächtigen Zeilen durchgeführt.
- **D10-Hinweis bestätigt:** Magnum/Grossformate bekommen durch diesen
  Fix jetzt tatsächlich ihre eigene `bottle_size_dl` (z. B. 15,0) statt
  stillschweigend als Standardflasche gezählt zu werden — genau die in
  D10 verlangte "eigene Reihe", jetzt auch technisch durchsetzbar.

**0.5 `price_per_bottle_eur` befüllen** (M)
- Formel: `realised_price / quantity / (bottle_size_dl/7.5)`, Basis gemäss D1; bei fehlendem `realised_price`: aus `hammer_price + buyer_premium` ableiten (`price_source=DERIVED`).
- `quantity IS NULL` → 1 mit Flag `qty_assumed`; `quantity > 12` → Flag `QTY_SUSPECT` (wahrscheinlich Mischlos / Kartons).
- Neue Spalten: `price_per_bottle_eur`, `ppb_flags`.
- AC (revidiert 2026-11-05, gleiches Prinzip wie D18): ~~≥ 85 % der
  `single_wine_prices` haben `price_per_bottle_eur`~~ — **jede Zeile
  ohne Wert hat einen erklärten, geflaggten Grund; keine stille Lücke.**
  Keine Werte ≤ 0 (geprüft, **erreicht: 0 Zeilen** in der ganzen DB).
- Test: Tabelle von Los-Konstellationen → erwarteter Flaschenpreis.
- **Status: erledigt 2026-11-05** (final gegen die Master-DB nachgebaut
  und verifiziert, inkl. zwei Review-Fix-Runden). `_fill_price_per_bottle`
  (neue Funktion in `build_db.py`, läuft nach `resolve_wines()`, da
  `bottle_size_dl`/`quantity`/`lot_kind` dort final werden). Fünf
  Befunde/Fixes über beide Review-Runden:
  1. `buyer_premium` gesetzt, aber `realised_price` dennoch NULL
     (bestwineauctions/ackerwines setzen beide Felder unabhängig) war
     ungeflaggt → eigenes Flag `NO_REALISED_PRICE` (statt mit
     `NO_PREMIUM_POLICY` verwechselt zu werden).
  2. `lot_kind='MIXED'` bekam fälschlich einen Flaschenpreis aus dem
     fingierten 7,5-dl-Default → ausgeschlossen, Flag `MIXED_LOT`
     (siehe auch 0.4-Fix 4, der den fingierten Wert selbst verhindert).
  3. `bottle_size_dl <= 0` (unvalidiert aus Rohdaten-Feldern einiger
     Loader) war ungeschützt (Crash-Risiko bei 0, falscher Wert bei
     negativ) → Flag `SIZE_SUSPECT`, keine Berechnung.
  4. **Eigener Befund (nicht von der Review, beim Verifizieren der
     Zahlen selbst gefunden): `ZERO_PRICE`.** Zeilen sind `sold=1` mit
     `hammer_price`/`realised_price` buchstäblich `0.0` — eine echte
     Zuschlagszeile, aber Preis null (kein donated/no-reserve-Fall, die
     hätten einen echten >0-Preis). Hätte sonst `price_per_bottle_eur=0`
     erzeugt und die eigene „keine Werte ≤ 0"-AC verletzt.
  5. **Review-Fix Runde 2: `NO_FX_RATE`.** `fx_status='MISSING'` (D18)
     wird nur gesetzt, wenn `lot_date IS NOT NULL`. Ein bepreistes Los
     mit bekannter Währung, aber ganz ohne `lot_date` hatte weder
     `fx_status` noch einen `ppb_flags`-Eintrag — eine stille,
     unerklärte Lücke, die auch nicht in der D18-FX-Lücke mitgezählt
     war. Eigenes Flag `NO_FX_RATE` (nur wenn `fx_status` die Lücke
     nicht schon erklärt).
  6. **Gate-G0-Fund (2026-11-06): die hier zitierten Zahlen waren
     zwischen `docs/` und den Code-/Test-Docstrings auseinandergelaufen**
     (66 689 vs. 70 825 `ZERO_PRICE`, 3 060 vs. 3 129 `NO_FX_RATE`) — in
     Wahrheit beide Seiten veraltet, da dieselbe Session später den
     Wermuth-sa-Spaltenversatz- und den Magnum-Bug (0.4) behoben hat,
     was die zugrunde liegenden Zeilen selbst verschoben hat. Alle drei
     Stellen (hier, `build_db.py`, `test_loader_roundtrip.py`) jetzt neu
     gegen die finale, dreifach nachgebaute Master-DB verifiziert und
     synchron.
  **Finales Live-Ergebnis** (nach allen Gate-G0-Fixes, `single_wine_prices`,
  3 234 509 Zeilen): **2 527 374 mit `price_per_bottle_eur` (78,13 % roh).**
  Lücke (707 135 Zeilen) vollständig erklärt, keine unerklärte Restmenge:
  479 685 **kein Preis** (weder `realised_price` noch `hammer_price`),
  151 059 **D18-FX-Lücke** (AUD/HKD vor Cache-Start, TWD-Datenabruf
  ausstehend), 66 726 **`ZERO_PRICE`** (davon 56 600 ackerwines),
  6 579 **`NO_PREMIUM_POLICY`** (winebarrel), 3 060 **`NO_FX_RATE`**
  (kein `lot_date`), 182 `quantity≤0`. **Von den Zeilen mit echtem Preis:
  2 527 374 / 2 754 824 = 91,74 %** bekommen `price_per_bottle_eur` — die
  aussagekräftige Zahl, unverändert gegenüber vor den Gate-G0-Fixes (die
  Fixes verschieben Zeilen zwischen den Ursachen, nicht den Gesamtanteil).
  Stichprobe (8 Zufallszeilen) manuell plausibilisiert (Preise CHF
  7–168/Flasche, alle positiv, passende Grössenordnung).
- **Los-Konstellationen-Tabelle (nachgeholt Gate G0, 2026-11-06)** — je
  eine echte Zeile aus der Master-DB pro Konstellation, Formel
  `realised_price / fx_rate / quantity / (bottle_size_dl/7,5)` händisch
  nachgerechnet und exakt bestätigt:

  | Konstellation | Beispiel (`realised_price`/`fx_rate`/`quantity`/`bottle_size_dl`) | `price_per_bottle_eur` | Flag |
  |---|---|---|---|
  | Standard, EUR, 1 Flasche | 129,78 / 1,0 / 1 / 7,5 | 129,78 | – |
  | Mehrere Flaschen, EUR | 3337,06 / 1,0 / 6 / 7,5 | 556,18 | – |
  | Magnum (15 dl) | 1155,62 / 1,0 / 1 / 15,0 | 577,81 | – |
  | Fremdwährung (CHF) | 1625,00 / 0,9356 / 1 / 7,5 | 1736,85 | – |
  | `price_source=DERIVED` (aus `hammer_price+buyer_premium`, von `_apply_premium_policy` **vor** diesem Schritt befüllt) | 17360,00 / 1,5634 / 1 / 30,0 | 2776,00 | – |
  | `lot_kind='MIXED'` | 102000,00 / 1,1346 / – / – | *(NULL)* | `MIXED_LOT` |
  | `lot_kind='UNKNOWN'` | 24000,00 / 1,1516 / – / – | *(NULL)* | `UNKNOWN_LOT` (Gate-G0-Fund) |
  | `hammer_price=realised_price=0.0`, `sold=1` | 0,0 / 1,0815 / 1 / 7,5 | *(NULL)* | `ZERO_PRICE` |
  | `quantity>12` (Mischlos-Verdacht) | 290,45 / 1,0 / 18 / 7,5 | 16,14 (trotzdem berechnet) | `QTY_SUSPECT` |

  **Präzisierung gegenüber der ursprünglichen Spec-Formulierung** (oben,
  „bei fehlendem `realised_price`: aus `hammer_price + buyer_premium`
  ableiten"): `_fill_price_per_bottle` selbst tut das nicht — es liest
  immer nur `realised_price` und flaggt `NO_REALISED_PRICE`/
  `NO_PREMIUM_POLICY`, wenn das NULL ist. Die Hammer+Premium-Ableitung
  passiert bereits **vorher**, in `_apply_premium_policy`
  (`price_source='DERIVED'`) — bestätigt am `DERIVED`-Beispiel oben, bei
  dem `realised_price` zum Zeitpunkt dieses Schritts schon befüllt ist.
- **Hinweis (unverändert):** Die Roh-Spalte `price_per_bottle` (nicht zu
  verwechseln mit `price_per_bottle_eur` oben, die mit diesem Schritt jetzt
  befüllt ist) existiert im Schema (Passthrough aus den Loadern), ist aber
  weiterhin in 100 % der Zeilen NULL — kein Ziel dieses Schritts, nur zur
  Abgrenzung festgehalten.

**0.6 Outlier- und Dubletten-Bereinigung** (M)
- Dubletten: gleiche (wine_ref_id, Jahrgang, Datum, Preis ±1 %, Haus) → eine Zeile; idealwine („cote") als eigene Preisart `price_kind='COTE'` ausschliessen oder getrennt führen (Entscheid in Review).
- Ausreisser: robuste z-Score (MAD) im Log-Preis je Gruppe, |z|>5 → `ppb_flags += 'OUTLIER'` (**nicht löschen**, nur markieren; Modell entscheidet).
- AC: Anzahl markierter/entfernter Zeilen pro Haus im Report; Stichprobe 50 markierte Zeilen manuell geprüft.
- **D20 (entschieden 2026-11-06): Dubletten-Regel geändert.** Die
  oben spezifizierte Wein-Identitäts-Regel (wine_ref_id/Jahrgang/Datum/
  Preis±1%/Haus, ohne lot_no) wurde live geprüft und erzeugt
  nachweisbare False Positives: (a) langtons verkauft wiederholt zwei
  einzelne Flaschen desselben Weins als separate, aufeinanderfolgende
  Lose zum selben Preis (dünner Markt, echte Marktdaten, keine Dublette
  — verifiziert an mehreren konkreten Beispielen); (b) ackerwines hat
  echte Zwillings-Konsignationen (zwei fast identische Lose, je eigene
  `lotId`); (c) selbst eine verschärfte Variante (exakter Match + "aus
  unterschiedlicher `source_file`") schlägt fehl, weil Häuser wie
  steinfels eine Auktion über mehrere `ResultfileN.json`-Seiten
  paginieren — jede Seite ist technisch eine "andere Quelldatei",
  obwohl es dieselbe Auktion ist (verifiziert: keine Lot-Überlappung
  zwischen den Seiten). **Entschieden: stattdessen die bereits
  bestehende, bewährte `_check_duplicate_lot_numbers`-Definition
  wiederverwenden** (gleiche `auction_id`+`lot_no`+voller Inhalt mehr
  als einmal) — `(auction_id, lot_no)` ist je Haus praktisch schon
  eindeutig, der volle Inhalt obendrauf macht einen False Positive
  praktisch ausgeschlossen. Markiert (niemals gelöscht), wie geplant.
- **Status: erledigt 2026-11-06** (final gegen die Master-DB
  nachgebaut und verifiziert). Drei neue Funktionen in `build_db.py`:
  `_flag_cote_prices` (D11: `price_kind='COTE'` für alle idealwine-
  Zeilen, eigene Spalte statt `ppb_flags`, da es eine Aussage über die
  Preis*art* ist, nicht über einen Berechnungsfehler), `_flag_duplicate_lots`
  (D20, s.o.; behält die erste Zeile pro Gruppe unverändert, flaggt den
  Rest `DUP_CANDIDATE`), `_flag_price_outliers` (robuster z-Score auf
  `ln(price_per_bottle_eur)` je `(wine_ref_id, vintage)`-Gruppe, Median/MAD
  statt Mittelwert/Stdabw. — genau die Grössen, die Ausreisser selbst
  verzerren würden; Gruppe braucht ≥ 5 Beobachtungen, MAD=0 wird
  übersprungen, nicht erzwungen). Alle drei hängen an `ppb_flags`
  (Komma-getrennt angehängt, nie überschrieben — ein Los kann schon ein
  Flag von `_fill_price_per_bottle` tragen, z. B. `QTY_SUSPECT,OUTLIER`
  oder `MIXED_LOT,DUP_CANDIDATE`, beide live verifiziert). AC-Report
  (`_report_06_flags`, läuft in `_validate_gates`) druckt Anzahl je
  Haus bei jedem Build.
  **Zwei Review-Runden, zwei echte Bugs gefunden und behoben:**
  Runde 1 fand, dass `_flag_price_outliers`s Vergleichsgruppen
  `price_kind='COTE'`-Zeilen (idealwine) mit echten Auktionspreisen
  mischten — Fix: `AND price_kind IS NULL` in der Gruppierung. Runde 2
  verschob `_flag_cote_prices`/`_flag_duplicate_lots` fälschlich vor
  `resolve_wines()` (mit der — beim Nachbau widerlegten — Begründung,
  das sei äquivalent zu `_check_duplicate_lot_numbers`); beim
  Verifizieren des Rebuilds selbst entdeckt: `_fill_price_per_bottle`
  schreibt `ppb_flags` nicht additiv, sondern mit einem schlichten
  `UPDATE ... ppb_flags=?`, das für jede Zeile mit Preis den gerade
  gesetzten `DUP_CANDIDATE`-Flag sofort wieder überschrieb (sichtbar als
  23 636→14 395 Zeilen, v. a. sylvies). Fix: `_flag_duplicate_lots` läuft
  jetzt nach `_fill_price_per_bottle` (beide weiterhin nach
  `resolve_wines()`, wegen bereinigter `wine`/`quantity`/`vintage_final`-
  Felder), mit eigenem Regressionstest, der genau diese Interaktion prüft.
  **Zahlen, Stand 2026-11-06 (vor Gate G0):** `DUP_CANDIDATE`
  23 636 Zeilen (deckt sich exakt mit dem unabhängig berechneten
  `_check_duplicate_lot_numbers`-Gate-Wert), Verteilung: ackerwines
  12 568, sylvies 10 994, winefields 34, franzwermuth 32, langtons 7,
  besch-cannes 1 — **unverändert durch Gate G0.** `OUTLIER` war an
  dieser Stelle 73 604 Zeilen (langtons 32 629, christies 19 909,
  ackerwines 8 679, Rest kleiner pro Haus) — **Gate G0 fand zwei weitere
  Kontaminations-Bugs in `_flag_price_outliers`'s Vergleichsgruppen**
  (unzuverlässiger `vintage_status` über den `COALESCE(vintage_final,
  vintage)`-Fallback statt nur `vintage_final`; `QTY_SUSPECT`-Zeilen
  nicht ausgeschlossen, obwohl `price_kind='COTE'` es schon war) und
  behob beide: **finale, am vierten Rebuild verifizierte Zahl `OUTLIER`
  67 258 Zeilen** (langtons 31 171, christies 16 174, ackerwines 8 553,
  Rest kleiner pro Haus). `price_kind='COTE'` 33 963 Zeilen (= alle
  idealwine-Lots, exakt wie erwartet, unverändert). Stichprobe
  (5 Zufalls-OUTLIER) manuell plausibilisiert
  (u. a. ein DOMAINE LEROY Grand Cru 1996 bei 18 656 EUR/Flasche —
  plausibel extrem für diesen Produzenten, nicht offensichtlich falsch).
  **Formale 50-Lose-Stichprobe nachgeholt in Gate G0** (2026-11-06,
  gegen die finale Master-DB): 30 zufällige `OUTLIER`-Zeilen (alle mit
  positivem `price_per_bottle_eur`, keine Anomalie) + 20 zufällige
  `DUP_CANDIDATE`-Zeilen (alle bestätigt mit einem echten Geschwister
  über `(auction_id, lot_no)`) — keine neuen Befunde.

**0.7 View `forecast_input`** (S)
- `select lot_id, wine_ref_id, vintage, size_class, lot_date, auction_id, provider_id, price_per_bottle_eur` mit `sold = 1` (D14), `lot_date IS NOT NULL`, `price_per_bottle_eur IS NOT NULL`, ohne `price_kind='COTE'` (D11), ohne `OUTLIER`/`QTY_SUSPECT`/`DUP_CANDIDATE` (0.6), nur Serien (`wine_ref_id`/`vintage`/`size_class`) mit letzter Beobachtung ≤ 36 Monate (D15). `y=ln(price_per_bottle_eur)` bewusst **nicht** in der View berechnet (SQLite-Mathefunktionen sind nicht überall aktiviert; gehört ohnehin in den Modell-Code, nicht in die Datenauswahl).
- AC: Zeilenbilanz Rohdaten → Input mit Verlust je Ursache (Tabelle), Summen stimmen.
- **Status: erledigt 2026-11-06** (final gegen die Master-DB nachgebaut
  und verifiziert). Baut auf `single_wine_prices` auf statt auf `lots`
  direkt, damit eine Zeile mit unzuverlässigem `vintage_status` (NV/MV/
  MISSING/AMBIGUOUS/CONFLICT/INVALID) nie unter einem falschen
  Serienschlüssel landet. `size_class` = `bottle_size_dl` direkt (D10).
  D15 per Fenster-Funktion `MAX(lot_date) OVER (PARTITION BY
  wine_ref_id, vintage_final, bottle_size_dl)`, verglichen gegen
  `date('now', '-36 months')` zur Abfragezeit (nicht zum Build-
  Zeitpunkt) -- eine Serie wird "inaktiv" allein durch verstreichende
  Zeit, ohne dass ein neuer Build nötig ist, genau wie sie durch den
  nächsten monatlichen Ingest wieder "aktiv" werden kann. 14 Tests
  (Builder-Setup + direktes `UPDATE` für die derived-only-Spalten,
  gleiche Konvention wie 0.5/0.6). AC-Report (`_report_07_
  forecast_input`, in `_validate_gates`) druckt die Zeilenbilanz bei
  jedem Build. **Live-Ergebnis, nach allen Gate-G0-Fixes (vierter
  Rebuild, 2026-11-06):** 4 297 347 Rohdaten-Zeilen ->
  `single_wine_prices` 3 234 509 (-1 062 838) -> `sold=1` 1 413 299
  (-1 821 210) -> `lot_date` 1 411 711 (-1 588) -> `price_per_bottle_eur`
  1 348 894 (-62 817) -> `price_kind IS NULL` 1 348 894 (-0: alle 33 963
  COTE-Zeilen haben bereits `sold≠1`, der Filter ist aktuell
  deckungsgleich damit, aber bewusst explizit gehalten, da es eine
  Zufallskorrelation der Daten ist, keine Schema-Garantie) -> ohne
  0.6-Flags 1 268 653 (-80 241) -> Serie aktiv (D15) **969 183**
  (-299 882), verteilt über 119 646 Serien, davon 82 956 Zeilen (8,6 %)
  mit `size_assumed=1` (neu ab Gate G0 mitgezählt, D21 offen). Summen
  stimmen (letzte Stufe = direkte `SELECT COUNT(*) FROM
  forecast_input`). Gate-G0-Fixes, die diese Zahlen gegenüber der
  ursprünglichen 0.7-Lieferung verschoben haben: Wermuth-sa-
  Spaltenversatz-Bug (0.4, siehe dort), Magnum/Double-Magnum-
  Grössenerkennung (0.4), `_flag_price_outliers`-Kontamination (0.6),
  und der D15-Fenster-Scope-Bug unten.
- **Gate-G0-Fund (2026-11-06): D15s Fenster-Funktion sah nur bereits
  gefilterte Zeilen.** `MAX(s.lot_date) OVER (PARTITION BY ...)` stand
  in derselben Subquery, deren `WHERE` schon OUTLIER/QTY_SUSPECT/
  DUP_CANDIDATE ausschloss — nach SQLs Standard-Auswertungsreihenfolge
  (WHERE vor Fenster-Funktionen) sah `MAX()` nur die bereits
  flag-bereinigten Zeilen. Eine Serie, deren einzige jüngste Beobachtung
  zufällig geflaggt war (ein echter, wenn auch z. B. preis-auffälliger
  Verkauf), wurde dadurch allein anhand ihrer älteren, unauffälligen
  Verkäufe beurteilt — und konnte fälschlich als "inaktiv" gelten,
  obwohl der Wein nachweislich noch gehandelt wird, mit der Folge, dass
  die GANZE Serie (inkl. sonst gültiger älterer Zeilen) aus
  `forecast_input` fiel. Fix: die Serien-Aktualität wird jetzt in einer
  separaten Subquery berechnet, die nur `sold=1`/`lot_date`/Preis/
  `price_kind IS NULL` prüft (nicht die 0.6-Flags) und per
  `wine_ref_id·vintage_final·bottle_size_dl` an die eigentliche,
  weiterhin voll gefilterte Zeilenauswahl angehängt wird. Neuer
  Regressionstest (`test_flagged_recent_row_still_keeps_series_active`).

**Gate G0:** Review aller Stufe-0-Schritte (§7). Ohne Freigabe kein Start von Stufe 1.

### Stufe 1 – Baselines & Evaluations-Harness

**1.1 Paket-Gerüst** (S): `data/forecast/{__init__,data.py,models.py,eval.py,run.py}`, `requirements` ergänzt (`pandas`, `numpy`, `statsmodels`, `scipy`), Versionen gepinnt.
- AC: `python -I -c "import statsmodels"` ok; CI-Workflow installiert Abhängigkeiten.

**1.2 Daten-Loader** (S): `load_series(conn, wine_ref_id, vintage, size_class)` → DataFrame (date, y, provider, qty); sortiert, deterministisch.
- Test: Reihenfolge, Zeitzonen-freie Daten, leere Serie.

**1.3 Haus-/Los-Effekte entfernen** (M): Einfaches Fixed-Effects-Modell über alle Daten: `y ~ wine·vintage + provider + log(qty) + size_assumed` (lineares Modell, `statsmodels.formula.api.ols` oder Within-Transformation). Haus-Offsets als Tabelle `provider_effects` speichern; Plausibilitätsprüfung gegen bekannte Premium-Unterschiede (§`premium-policy.md`).
- AC: Haus-Offsets liegen in plausiblem Bereich (|offset| < ln(1,5)); Residual-Varianz sinkt gegenüber Rohdaten (Report).

**1.4 Baselines** (S): (a) Last-Value, (b) Median der letzten k Lose, (c) gleitender Median 12 M, (d) saisonfreie lineare Trend-Regression im Log. Alle liefern Quantile via empirische Residuen.
- Test: Konstante Serie ⇒ Prognose konstant, Intervallbreite 0.

**1.5 Rolling-Origin-Evaluator** (M)
- Origins: alle Jahres-/Halbjahresgrenzen der letzten 24 M; je Origin nur Daten `< origin`; Targets = Beobachtungen in `[origin, origin+Horizont)`.
- Metriken: MAPE (EUR), MdAPE, Pinball-Loss (q=0,1/0,5/0,9), Winkler-Score, Coverage je Nominal, Intervallbreite (median), Aufteilung nach Dichteklasse und Haus.
- Test: `test_no_lookahead` (G1), `test_metric_known_values`.
- AC: Baseline-Report als Tabelle in `docs/forecast-baseline-report.md` (reproduzierbar per Befehl).

**Gate G1:** Baseline-Zahlen im Review festgeschrieben = die Latte für alles Weitere.

### Stufe 2 – Local-Level-Modell (Kern)

**2.1 Dichte-Schwellen kalibrieren** (S): Backtest: ab welchem `n_obs`/Spanne schlägt Local-Level die Baselines? D5 wird mit den Zahlen belegt.

**2.2 Irregulärer Zeitschritt** (L, **Kernrisiko**)
- `UnobservedComponents('llevel')` von statsmodels erwartet gleichabständige Daten. Optionen:
  A) auf Monatsraster aggregieren, fehlende Monate als NaN (Kalman behandelt Lücken korrekt, Varianz wächst) – **empfohlen**;
  B) eigener Kalman-Filter mit `Δt`-abhängiger Prozessvarianz `σ²_η·Δt`.
- Messvarianz σ²_ε (Auktionsrauschen) und Prozessvarianz σ²_η (Drift des „wahren Wertes") per ML schätzen; Untergrenzen für σ² (gegen Degeneration auf 0 = Scheingenauigkeit).
- Mehrere Lose im selben Monat: als mehrere Beobachtungen mit identischem Zeitpunkt (Option B) oder Mittel + Gewicht nach Anzahl (Option A) – Entscheid mit Test.
- Test: Synthetische Serie mit bekannten σ²: Schätzung innerhalb ±30 %; Lücke von 24 M ⇒ Prognoseintervall breiter als bei Lücke 1 M.

**2.3 Konvergenz-Handling** (M): Fehlgeschlagene Fits → Flag `FIT_FAILED`, Fallback Stufe 3. Zähler im Report; Quote > 5 % ⇒ Review.

**2.4 Prognose-Verteilung** (S): Aus Zustandsverteilung am Ziel-Zeitpunkt: Median, Quantile q05–q95 im Log, Rücktransformation. **Prädiktions-** nicht Konfidenzintervall (Messrauschen einrechnen!). Test: Intervall ≥ Messrauschen-Intervall.

**2.5 Vergleich gegen Baselines** (M): Eval-Harness aus 1.5.
- AC (G2): Pinball-Loss < beste Baseline in ≥ 60 % der Gruppen; Coverage 80 % ∈ [77, 83].

**2.6 Zusatz: Trend-Komponente testen** (M): `local linear trend` vs. `local level`; nur übernehmen, wenn nach G2 besser. Dämpfung zwingend (Trend-Extrapolation über 12 M kann Fantasiepreise liefern).

**Gate G2:** Senior-Review mit Plots (Fan-Charts) der 30 Gold-Set-Weine.

### Stufe 3 – Gruppenindex & Fallback

**3.1 Gruppen-Definition** (S): Hierarchie `region > producer > vintage`; Mindestgrösse je Ebene; Ebenen-Auswahl datengetrieben (kleinste Ebene mit ≥ N Beobachtungen).

**3.2 Repeat-Sales-Index** (L): Wiederverkaufspaare gleicher (Wein, Jahrgang, Format) ⇒ Regression `Δln P = Σ β_t·D_t` (Case-Shiller, Gewichtung nach Zeitabstand, da Varianz mit Abstand wächst). Index monatlich, Basis 100.
- Test: Synthetischer Index (bekannter Trend) wird innerhalb Toleranz rekonstruiert.
- Hinweis: Auktions-Wiederverkäufe der *selben Flasche* sind nicht identifizierbar; gleiche Wein·Jahrgang-Kombinationen sind der Proxy. Das ist **kein** echter Repeat-Sales-Index → in der Doku so benennen („Pseudo-Repeat-Sales").

**3.3 Index-Prognose** (M): Index per Local-Level fortschreiben; Wein-spezifisches Niveau = Index × Gruppenniveau (letzter geschätzter Level oder Hierarchie-Shrinkage).

**3.4 Hierarchisches Shrinkage** (M): Empirical-Bayes: Niveau/Varianz je Wein werden zum Gruppenmittel geschrumpft, Gewicht ∝ `n_obs`. (Voll-Bayes mit PyMC/Stan nur falls EB nicht genügt – bewusst späterer Schritt, nicht v1.)

**3.5 Fallback-Intervall** (S): Streuung = Gruppen-Residuenstreuung × Aufschlag; Flag `GROUP_INDEX`.

**3.6 Evaluation Dünn-Fälle** (M): Separate Metriken für n_obs ∈ {1–2, 3–4, 5–9}. AC: Coverage ±3 pp auch hier; wenn nicht erreichbar ⇒ `INSUFFICIENT_DATA` für diese Klasse (dann ist das das Ergebnis, kein Fehler).

**Gate G3:** Review: Wo ist „genügend" wirklich? Definition der finalen Produktabdeckung.

### Stufe 4 – Konforme Kalibrierung

**4.1 Konforme Residuen** (M): Split-/Rolling-Conformal auf den Out-of-Sample-Fehlern der Backtests, nach Dichteklasse und Horizont gruppiert (`mondrian conformal`). Intervall = Modell-Median ± Quantil der absoluten Log-Fehler.
**4.2 Nachweis** (S): Coverage-Tabelle je Horizont, Haus, Dichteklasse; Abweichungen > 3 pp dokumentiert.
**4.3 Drift-Monitor** (S): Bei jedem Lauf Coverage der *eingetretenen* Prognosen der Vorperiode messen; < 70 % bei 80 %-Intervallen ⇒ Warnung im Run-Report.

### Stufe 5 – Serving

**5.1 Tabelle `price_forecasts`** (M): `wine_ref_id, vintage, size_class, horizon, q05..q95, median, method, n_obs, last_obs_date, flags, model_version, created_at`. Idempotent (Upsert pro Schlüssel+Version).
**5.2 Runner** (M): `python3 data/forecast/run.py --db … --out …` (atomar, tmp + `os.replace`), Fortschritts-Log, Run-Report (Zählbilanz G4).
**5.3 CI-Anbindung** (S): Nach `process.yml` (DB-Build) als Folgeschritt, Artifact; **nicht** Teil von `ingest.yml`.
**5.4 API-Endpoint** (M): `GET /wines/{id}/forecast` in `api/main.py`; Antwort ohne Punktwert bei `INSUFFICIENT_DATA`. Test in `api/test_main.py`.
**5.5 UI** (M): Fan-Chart (Historie + Quantilbänder), klare Beschriftung „Schätzung, keine Anlageberatung", sichtbares Flag bei `GROUP_INDEX`/`EXTRAPOLATION`.

---

## 6. Offene Entscheidungen (vor Start klären)

| # | Frage | Folge |
|---|---|---|
| D10 | Magnum/Grossformate: eigene Serien oder Äquivalent-Faktor ×(Vol/0,75)? | Beeinflusst 0.4/0.5, Preise sind nicht linear im Volumen |
| D11 | idealwine „cote" (Schätzwert, kein Zuschlag) in die Serien? | Vermischt Beobachtung mit Schätzung; Empfehlung: ausschliessen |
| D12 | Währung der Anzeige: EUR oder Heimwährung des Hauses? | UI-Frage, Modell rechnet in EUR |
| D13 | FX-Quelle und Auflösung (monatlich vs. täglich)? | Stufe 0.2 |
| D14 | `sold IS NULL` (62 %): als verkauft werten? | Haus-Audit nötig; sonst Zensur-Verzerrung unbekannt |
| D15 | Fokus auf Produktabdeckung: nur Bestandsweine mit Aktivität ≤ 36 M? | Verhindert Prognosen für „tote" Weine |
| D16 | `fx_rate` für EUR-Zeilen (569 131 Zeilen, 13 %): NULL oder 1.0? | Beeinflusst 0.5-Formel (Sonderfall nötig oder nicht) |
| D17 | winebarrel-Epoch-Artefakt (`lot_date='1970-01-01'`, 680 Zeilen, Rohdaten selbst korrupt, kein Backfill möglich) | 0.1b/0.7 |
| D18 | 0.3-AC (≥ 99 %) nicht erreichbar (96,04 %) wegen struktureller EODHD-Lücke vor Cache-Start (AUD vor 2006-03-01, 158 920 Zeilen; HKD vor 1999-12-31, 261 Zeilen) — AC-Zahl senken, Zeilen explizit als `fx_status='MISSING'` dokumentieren und aus `forecast_input` ausschliessen, oder eine zweite FX-Quelle für die Vor-Cache-Spanne suchen? | 0.3/0.7, AC-Formulierung |
| D19 | zacky's `bottle_size_dl=1.0`-Bug (24 129 Zeilen): `parse_dl` bekam das `quantity`-Feld (Flaschenzähler, z. B. "6") statt eines Size-Felds übergeben und las die blanke Zahl über seinen Zahlen-Fallback fälschlich als dl-Wert. Keine echte Alternative abzuwägen — reiner Bug, nur eine sinnvolle Behebung (Guard vor `parse_dl`, siehe 0.4). | 0.4 |
| D20 | 0.6-Dubletten-Regel: wine-Identitäts-Heuristik (wine_ref_id/Jahrgang/Datum/Preis±1%/Haus) erzeugt live bestätigte False Positives (echte Zwillings-Lose bei langtons/ackerwines, Pagination bei steinfels) — stattdessen `_check_duplicate_lot_numbers`s bestehende (auction_id, lot_no, voller Inhalt)-Definition wiederverwenden? | 0.6 |
| D21 | `size_assumed=1` (kein Grössen-Hinweis in den Rohdaten, `_assume_default_bottle_size` setzt 7,5 dl als Default) macht ~38 % aller `SINGLE`-Lose aus (Gate-G0-Fund, 2026-11-06, Code-Review). `forecast_input` behandelt diese Zeilen aktuell identisch zu einer bestätigten 7,5-dl-Flasche — nur gezählt/reported (`_report_07_forecast_input`), nicht ausgeschlossen oder separat geflaggt. Ausschliessen (verliert einen grossen, mutmasslich meist korrekten Anteil echter 750-ml-Flaschen) oder als eigenes `ppb_flags`-Flag markieren (Modell entscheidet, wie 0.6) oder so lassen (750 ml ist die weit überwiegende reale Grösse, der Default ist kein Rateversuch ins Blaue)? | 0.7, Stufe 1-2 (Feature `size_assumed`?) |

**Entschieden am 2026-10-29:**
D10 Grossformate = **eigene Reihen** (Schlüssel `wine_ref_id · vintage · size_class`, kein Äquivalent-Faktor) ·
D11 idealwine-`cote` / Schätzwerte = **nicht in die Serien** (`price_kind='COTE'` ausgeschlossen) ·
D13 FX-Quelle = **EODHD** (vorhandenes Abo; API-Key nur via Umgebungsvariable, nie im Repo; Quelle/Abrufdatum in der Doku festhalten) ·
D14 `sold IS NULL` = **nicht werten** (Filter in `forecast_input`: `sold = 1`; Folge: ~62 % der Zeilen entfallen → Dichte in §2.10 neu messen, siehe 0.7).

**Entschieden am 2026-11-05:**
D12 Anzeigewährung = **nur EUR** (entspricht direkt D1/der Modell-Berechnung; keine Umrechnung in Heimwährung des Hauses in v1) ·
D15 Produktabdeckung = **nur aktive Weine** (letzte Beobachtung ≤ 36 M, wie in D5 für Stufe 2 bereits verlangt — gilt jetzt auch für den Gruppenindex-Fallback aus Stufe 3: ein „totes" Wein-Jahrgang bekommt keine Prognose, auch keine breite) ·
D16 `fx_rate` für EUR = **1.0 setzen** (nicht NULL) — einheitliche Formel in 0.5 (`preis_eur = preis_ccy / fx_rate`), kein Sonderfall nötig, kein Risiko dass EUR-Zeilen bei einem vergessenen Sonderfall stillschweigend NULL werden ·
D17 winebarrel-1970-Epoch = **`lot_date` auf NULL setzen** — einzig technisch mögliche Option (Rohdaten enthalten buchstäblich `"auction_end": "1970-01-01 01:00:00"`, kein zweites Datumsfeld im Lot, `auction_date` der virtuellen "all"-Auktion ist selbst NULL); betrifft `forecast_input` ohnehin nicht, da alle 680 Zeilen `sold IS NULL` haben (→ D14) ·
D18 FX-AC-Lücke = **AC senken + Zeilen flaggen** (nicht: zweite FX-Quelle suchen) — `fx_status='MISSING'` (neue Spalte + CHECK-Constraint) für jede Zeile mit bekannter Währung und `lot_date`, aber ohne `fx_rate`; die AC-Formulierung in 0.3 wechselt von einer festen Prozentzahl zu „jede Lücke ist erklärt und geflaggt, keine stille NULL" (Guardrail G3) ·
D19 zacky-Bug = **behoben** (`zacky_bottle_size_dl`-Guard, siehe 0.4) — kein Entscheid im eigentlichen Sinn, hier nur zur Nachvollziehbarkeit mitgeführt. Die 0.5-AC folgt demselben D18-Prinzip (AC-Formulierung statt Prozentzahl, siehe 0.5) — bekommt bewusst keine eigene D-Nummer, da es dieselbe bereits getroffene Entscheidung ist, nur ein zweites Mal angewendet.

**Entschieden am 2026-11-06:**
D20 Dubletten-Regel = **`_check_duplicate_lot_numbers`-Definition wiederverwenden** (nicht: Wein-Identitäts-Heuristik, auch nicht deren verschärfte Variante) — siehe 0.6 für die live-verifizierte Begründung (beide Heuristiken erzeugten nachweisbare False Positives, (auction_id, lot_no) + voller Inhalt praktisch nicht).

D10–D20 sind damit getroffen. D21 ist **offen** — bewusst nicht im Rahmen von Gate G0 entschieden, da sie 38 % der Daten betrifft und eine Produktentscheidung ist, keine reine Code-Korrektur; `_report_07_forecast_input` zählt die betroffenen Zeilen jetzt zumindest sichtbar (siehe 0.7-Status).

---

## 7. Senior-Review-Verfahren

Ablauf je Gate (G0–G3 + Abschluss):

1. **Selbst-Check** (Autor): Checkliste unten komplett abhaken, Ergebnis im PR.
2. **Mechanischer Review:** `/code-review high` auf dem Branch; Tests grün; `git diff --stat` ohne unerwartete Dateien (Working Tree ist aktuell dirty! → Arbeit auf eigenem Branch `feat/forecast`, nur Plan-relevante Dateien stagen).
3. **Fach-Review (Senior):** Review-Fragen je Gate:
   - G0: Stimmen Flaschenpreise stichprobenartig mit Originalquelle? FX-Quelle belegbar? Verlust-Bilanz plausibel?
   - G1: Ist die Evaluation leckfrei? Sind Baselines fair (nicht absichtlich schwach)?
   - G2: Passen Fan-Charts zu Marktintuition? Werden Intervalle bei Lücken breiter? Degenerierte σ² = 0 ?
   - G3: Wo ist die Grenze „genügend"? Sind Fallback-Intervalle ehrlich?
   - Abschluss: Coverage nachgewiesen? Dokumentation vollständig?
4. **Adversarial Check** (optional, unabhängig): Zweiter Reviewer erhält Code + Report ohne Autor-Schlussfolgerung (Verankerung vermeiden).
5. **Review-Log** in diesem Dokument (§8) mit Datum, Reviewer, Befunde, Entscheide.

**Vollständigkeits-Checkliste (je Stufe):**
- [ ] Alle Micro-Steps der Stufe mit AC erfüllt (Beleg: Befehlsausgabe im PR)
- [ ] Tests neu + bestehende grün; keine übersprungenen/xfail ohne Begründung
- [ ] Zeilenbilanzen stimmen (nichts verschwindet still)
- [ ] Flags/Statuswerte dokumentiert und getestet
- [ ] Determinismus-Test (G5) grün
- [ ] Backup vor Schema-Änderung vorhanden
- [ ] `docs/` aktualisiert (Runbook-Eintrag für den Lauf)
- [ ] Bekannte Verzerrungen (D7, Selektion, Haus-Mix) im Report benannt

---

## 8. Review-Log

| Datum | Gate | Reviewer | Befunde | Entscheid |
|---|---|---|---|---|
| 2026-11-06 | G0, Runde 1 | Claude (Autor-Stichproben: 0.4 100-Lose, 0.5 Los-Konstellationen, 0.6 50-Lose) | 127 verdächtige „1,0 dl"-Zeilen voll aufgeklärt (64 echter Bug, 63 echte Mini-Formate); 1 neuer echter Bug (Wermuth-sa-Spaltenversatz, verfälschte auch `hammer_price`, 215 Zeilen) | Fix + 5 Tests + Rebuild verifiziert |
| 2026-11-06 | G0, Runde 2 | Claude (`/code-review high`, Multi-Agent: 2 parallele Durchläufe, 8 Finder-Winkel je Durchlauf plus Straggler-Agenten, insg. ~20 Teilagenten) | 1. Durchlauf (committeter Branch-Diff): 11 Befunde, 3 echte Bugs (UNKNOWN-Lose fingiert bepreist, Outlier-Vergleichsgruppen-Kontamination, D15-Fenster-Scope-Bug). 2. Durchlauf (neue, unkommittierte G0-Fixes selbst re-geprüft): 4 Reuse-Befunde (sofort behoben) + danach 3 weitere, von Straggler-Agenten gemeldete **echte Bugs in den soeben selbst geschriebenen Fixes**: (a) `_BARE_FORMATS`-Kollisionen (DEMI/HALF/BALTHAZAR/MELCHIOR/DM lesen echte Markennamen/Text als Flaschenformat), (b) `parse_bottle_format`-Präzedenz (ein schwacher Bare-Word-Treffer in `name` blockierte einen starken Treffer in `description`), (c) Wermuth-Validated-CSV: ein leeres Trailing-Feld wurde als echte 11. Spalte gezählt (2 weitere falsch gelesene Zeilen). Dritter Durchlauf (finaler Diff): 1 weiterer echter Bug (`strip_bottle_format` wendet die Compound-Normalisierung nicht an, liess "Double-Magnum"-Text im Weinnamen stehen → Wein-Identitäts-Fragmentierung). Alle committeten Reuse-/Altitude-Befunde (Dreifach-`instr()`-Duplikat, `_flag_duplicate_lots`/`_check_duplicate_lot_numbers`-Logikduplikat, `zacky`/`winebarrel`-Wrapper-Architektur, `_assume_default_bottle_size` vs. `quantity`-Default-Asymmetrie, MAD=0-Mehrheitsverzerrung bei `_flag_price_outliers`) als Tech-Debt dokumentiert/vertagt, kein aktiver Schaden nachgewiesen. | 6 weitere echte Bugs gefixt (insg. **9 echte Bugs über beide G0-Runden**) + 12 weitere Tests + Index `idx_lots_wine_ref_vintage_size` + `forecast_input`-View als Single-Pass-CTE statt Join + `_report_07`-Query-Merge; 1 Restfund dokumentiert statt gefixt (Mehrfach-Wein-Freitextlisten können `quantity` mit einer Jahrgangszahl verwechseln -- betrifft nur `lot_kind='MIXED'`, bekommt nie einen Flaschenpreis, daher kein Preis-Risiko); D21 (`size_assumed`-Ausschluss) als offene Produktentscheidung dokumentiert statt entschieden. **G0 freigegeben, Stufe 1 kann starten.** |

---

## 9. Reihenfolge & Aufwand (grob)

Stufe 0: 3–4 Tage · Stufe 1: 2 Tage · Stufe 2: 3–4 Tage · Stufe 3: 4–5 Tage ·
Stufe 4: 1–2 Tage · Stufe 5: 3 Tage ⇒ **≈ 3–4 Wochen**, wovon Stufe 0 der
unvermeidbare und risikoreichste Teil ist. Ein erstes, vorzeigbares Ergebnis
(Gate G2, Fan-Charts für dichte Weine) liegt nach ca. 10 Arbeitstagen vor.
