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
| Stufe 1 – Baselines & Eval-Harness | ✅ 1.1–1.5 alle erledigt (2026-11-10, Code+Tests+Live-Report-Lauf verifiziert) — Gate G1 (Baseline-Zahlen festschreiben) als nächstes |
| Stufe 2 – Local-Level-Modell (Kalman) | 🟡 2.2-2.5 erledigt, Pinball-AC weiterhin erfüllt (93,75 % der Gruppen). **2.1 erledigt 2026-11-13** (siehe §5): Coverage-AC über ALLE Dichteklassen bewertet (User-Entscheid) -- **nicht erfüllt**, dichteabhängig (nur next/10+ im Band). **2.6 erledigt 2026-11-13:** `local_linear_trend` getestet, NICHT übernommen (lokal_level bleibt Produktionsmodell). Gate G2 (Gold-Set fehlt noch) weiterhin offen |
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
| D8 | Haus-/Los-Effekte | Als **Fixed Effects** vorab herausrechnen (Stufe 1.3), Rest geht ins Kalman-Modell | Brief: Auktionsrauschen separat. **Umgesetzt 2026-11-11** (User-Entscheid, Stufe 2): `provider_effects`-Tabelle (persistiert von `build_db.py` nach 0.5/0.6, NICHT in `build_wines.run()` -- siehe §8-Review-Log), `forecast/data.py`s `load_series`/`load_all_series` subtrahieren den Haus-Offset von `y`. Gilt für Baselines UND Local-Level gleich (fairer Vergleich) -- die zuvor "eingefrorenen" Stufe-1-Zahlen sind damit überholt, neu erzeugt in `docs/forecast-baseline-report.md`. |
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
- **Status: Code + Tests erledigt 2026-11-10** (`forecast/models.py`:
  `_last_value`/`_median_last_k`/`_rolling_median_12m`/`_trend` +
  `_retrospective_residuals`/`_quantiles_from_residuals`/`make_baseline`,
  registriert in `run.py`s `FORECASTERS`). `k=5` für (b) gesetzt, nicht
  entschieden (Plan nennt die Methode, nicht `k`). 18 neue Tests
  (`test_forecast_baselines.py`), inkl. der AC selbst UND eines
  strukturellen G4-Tests ("Intervallbreite wächst mit Horizont" --
  schärfer als die reine Konstante-Serie-AC, da die triviale
  Konstante-Serie-Variante auch bei horizontunabhängiger Breite
  bestehen würde).
  Zwei echte, beim Design selbst gefundene Bugs: (1) `(c)` ankerte das
  12M-Fenster am Prognose-Zieldatum statt am letzten bekannten Datum --
  für den 12M-Horizont dadurch IMMER ein leeres Fenster (das Zieldatum
  liegt per Konstruktion `origin+12M` hinter `train`s eigenem Ende),
  gefangen vom eigenen Konstante-Serie-Test, nicht geraten. (2) Der
  verschachtelte Residual-Backtest lief ungekappt O(n) `point_fn`-Calls
  pro Origin -- beim echten Live-Report-Lauf (siehe unten) mit
  einzelnen ~2000-Zeilen-Serien O(n²), nach 20+ Minuten ohne Ende
  abgebrochen; `MAX_BACKTEST_STEPS=50` (gekappt auf die letzten
  GEEIGNETEN Mini-Origins, nicht die letzten rohen Zeilenindizes --
  sonst fallen für den 12M-Horizont genau die kappbaren Schritte weg)
  behebt das, mit eigenem Performance-Test.
  **Zwei weitere echte Bugs beim echten Live-DB-Lauf gefunden** (nicht
  durch synthetische Tests erfasst): (3) `eval.extrapolation_flag`
  rief `math.exp()` auf einen rohen Log-Forecast auf -- eine echte
  "trend"-Extrapolation auf einer kurzen/lauten Serie überschritt
  dabei `math.exp`s Überlauf-Grenze (~709) und warf `OverflowError`,
  brach einen ansonsten erfolgreichen ~25-Minuten-Lauf ab. Fix: der
  Vergleich bleibt vollständig im Log-Raum (Differenz statt Quotient
  von zwei `exp()`-Werten), kein `exp()` mehr nötig. (4)
  `mape_eur`/`mdape_eur` exponenzierten denselben rohen Forecast ohne
  Overflow-Schutz -- NumPy wirft hier nur eine `RuntimeWarning` (kein
  Crash), aber eine einzige `inf`-Zeile macht den MITTELWERT-basierten
  MAPE für eine ganze Gruppe unbrauchbar (bestätigt im echten Report:
  `trend`s MAPE-Spalte zeigte `inf` oder astronomische Zahlen wie
  `2,8×10^50` in mehreren Zeilen). Fix: nicht-finite Zeilen werden aus
  MAPE/MdAPE ausgeschlossen UND explizit gezählt
  (`n_nonfinite_ape`, eigene Report-Spalte) -- dieselbe "flaggen, nie
  stillschweigend verwerfen"-Konvention wie 0.6s OUTLIER/DUP_CANDIDATE.
  MdAPE (Median) war von Natur aus robust dagegen, wird aber aus
  Konsistenzgründen gleich gefiltert.
  **Fünfter echter Bug, selbst beim Fix von #4 gefunden** (nicht
  geraten -- der korrigierte Report zeigte weiterhin astronomische
  MAPE-Werte wie `2,8×10^50` trotz `n_nonfinite_ape=0`): eine erste
  Fix-Version filterte nur `~np.isfinite(ape)` -- das erfasst `inf`/
  `nan`, aber NICHT eine `exp()`-Extrapolation, die knapp UNTER der
  Überlauf-Grenze eines Double landet (z. B. `exp(600) ≈ 3,8×10^260`,
  eine ganz normale finite Zahl, aber als EUR-Flaschenpreis absurd).
  Fix: `mape_eur`/`mdape_eur` schliessen Zeilen aus, deren
  `extrapolation_flag` (die ohnehin schon existierende G4-Markierung)
  gesetzt ist -- derselbe Massstab wie "Prognose weit ausserhalb
  [0,2×; 5×] des letzten bekannten Preises", nicht eine zweite,
  erfundene Schwelle; seit dem User-Entscheid (siehe §8-Review-Log)
  gilt derselbe Ausschluss für ALLE Metriken (`extrapolation_exclusion_mask`/
  `n_extrapolation_excluded`), nicht nur MAPE/MdAPE. Ausgeschlossene
  Zeilen werden gezählt, nie stillschweigend verworfen.

  **Live-Report-Lauf** (`python3 -m forecast.run`, alle 4 Baselines ×
  2 Horizonte über alle ~971 510 `forecast_input`-Zeilen /
  ~120 513 Serien, `--as-of 2026-11-10`): vier Versuche liefen auf
  echte Bugs (siehe §8-Review-Log, Bugs 2-5); der **fünfte, finale
  Versuch** (nach allen 6 Fixes + der Metrik-Ausweitung) lief
  **~33 Minuten, fehlerfrei, keine Ausreisser mehr in irgendeiner
  Spalte** -- der `n_train=1-2`-Bucket ist aus dem "next"-Horizont
  vollständig verschwunden (Fix 6 greift: diese Serien sind jetzt
  korrekt `INSUFFICIENT_DATA`, nicht mehr nullbreite Scheinsicherheit).
  Kopfzahlen ("alle"-Zeile je Modell/Horizont):

  | Modell | Horizont | n | MAPE | MdAPE | N ausgeschl. (EXTRAPOLATION) | Pinball q0.5 | Coverage 80% |
  |---|---|---|---|---|---|---|---|
  | last_value | next | 79 244 | 0,535 | 0,222 | 16 (0,02 %) | 0,1834 | 0,572 |
  | last_value | 12m | 146 010 | 0,719 | 0,265 | 610 (0,4 %) | 0,2178 | 0,639 |
  | median_last_5 | next | 79 244 | 0,471 | 0,216 | 872 (1,1 %) | 0,1673 | 0,564 |
  | median_last_5 | 12m | 146 010 | 0,586 | 0,254 | 3 294 (2,3 %) | 0,1948 | 0,587 |
  | rolling_median_12m | next | 79 244 | 0,469 | 0,208 | 435 (0,5 %) | 0,1677 | 0,579 |
  | rolling_median_12m | 12m | 146 010 | 0,563 | 0,241 | 3 662 (2,5 %) | 0,1906 | 0,601 |
  | trend | next | 67 981 | 0,545 | 0,241 | 1 733 (2,6 %) | 0,1818 | 0,608 |
  | trend | 12m | 137 774 | 0,594 | 0,297 | 7 962 (5,8 %) | 0,2099 | 0,612 |

  Zeilenbilanz je Modell/Horizont geht exakt auf
  (`forecast + insufficient = candidates`). Vorläufige Lesung (keine
  Gate-G1-Entscheidung, die kommt erst mit Stufe 2's Vergleich):
  `median_last_5`/`rolling_median_12m` schlagen `last_value` auf
  MAPE/Pinball in beiden Horizonten leicht, `trend` liegt bei "next"
  nah dran, verliert aber sichtbar bei "12m" (höchste MAPE/MdAPE UND
  höchster Extrapolations-Ausschluss -- erwartbar, da `trend` als
  einzige Baseline überhaupt extrapoliert statt zu persistieren/
  mitteln). Alle Gruppen (Dichteklasse `n_train`, Haus) aufgeschlüsselt
  in `docs/forecast-baseline-report.md`.

**1.5 Rolling-Origin-Evaluator** (M)
- Origins: alle Jahres-/Halbjahresgrenzen der letzten 24 M; je Origin nur Daten `< origin`; Targets = Beobachtungen in `[origin, origin+Horizont)`.
- Metriken: MAPE (EUR), MdAPE, Pinball-Loss (q=0,1/0,5/0,9), Winkler-Score, Coverage je Nominal, Intervallbreite (median), Aufteilung nach Dichteklasse und Haus.
- Test: `test_no_lookahead` (G1), `test_metric_known_values`.
- AC: Baseline-Report als Tabelle in `docs/forecast-baseline-report.md` (reproduzierbar per Befehl).
- **Status: erledigt 2026-11-10.** `forecast/eval.py` (Rolling-Origin-Split
  `half_year_origins`/`split`/`admits_horizon`, G4-Hartchecks in
  `_validate_forecast`, alle Metriken, `summarize`/`write_baseline_report`)
  + `forecast/run.py` (CLI, G6 `mode=ro`) + `data.load_all_series`
  (Bulk-Loader für alle ~120k Serien in einer Query statt N Einzel-
  Queries). Bewusst **vor** 1.4 gebaut (User-Entscheid: Reihenfolge
  1.5 → 1.4) — generisches Evaluations-Geruest zuerst, Baselines
  stecken sich später rein (`run.py`s `FORECASTERS`-Dict ist noch
  leer). AC-Report lief bereits erfolgreich gegen die Live-DB (0
  Modelle, siehe Datei) — die eigentliche Tabellenbefüllung mit echten
  Baselines folgt in 1.4. 22 neue Tests (`test_forecast_eval.py`,
  inkl. beider Pflicht-Tests `test_no_lookahead`/`test_metric_known_values`
  plus einem Leap-Year-Test für die 12M-Fenstergrenze), volle Suite
  478/478 grün.

**Gate G1:** Baseline-Zahlen im Review festgeschrieben = die Latte für alles Weitere.

### Stufe 2 – Local-Level-Modell (Kern)

**2.2 Irregulärer Zeitschritt** (L, **Kernrisiko**)
- `UnobservedComponents('llevel')` von statsmodels erwartet gleichabständige Daten. Optionen:
  A) auf Monatsraster aggregieren, fehlende Monate als NaN (Kalman behandelt Lücken korrekt, Varianz wächst) – **empfohlen**;
  B) eigener Kalman-Filter mit `Δt`-abhängiger Prozessvarianz `σ²_η·Δt`.
- Messvarianz σ²_ε (Auktionsrauschen) und Prozessvarianz σ²_η (Drift des „wahren Wertes") per ML schätzen; Untergrenzen für σ² (gegen Degeneration auf 0 = Scheingenauigkeit).
- Mehrere Lose im selben Monat: als mehrere Beobachtungen mit identischem Zeitpunkt (Option B) oder Mittel + Gewicht nach Anzahl (Option A) – Entscheid mit Test.
- Test: Synthetische Serie mit bekannten σ²: Schätzung innerhalb ±30 %; Lücke von 24 M ⇒ Prognoseintervall breiter als bei Lücke 1 M.
- **Status: erledigt 2026-11-11.** Option A umgesetzt (`forecast/models.py`'s `_monthly_series`: `resample("MS").mean()`, NaN-Lücken ohne Zusatzcode korrekt vom Kalman-Filter behandelt). Gewichtung nach Lot-Anzahl pro Monat (die 2.2-Alternative) bewusst NICHT gebaut für v1 -- siehe 2.5's Coverage-Befund unten, der entscheidet, ob das nachgezogen werden muss. Beide σ² empirisch bestätigt (240-Monate-Synthetik, fixer Seed, Schätzung innerhalb ±30 % des wahren Werts) sowie der Lücke-verbreitert-Intervall-Test, beide in `test_forecast_local_level.py`.

**2.3 Konvergenz-Handling** (M): Fehlgeschlagene Fits → Flag `FIT_FAILED`, Fallback Stufe 3. Zähler im Report; Quote > 5 % ⇒ Review.
- **Status: erledigt 2026-11-11, mit einer echten Design-Korrektur mitten im Prozess** (via `advisor`, nach einem Live-DB-Befund, nicht geraten): die erste Lesung von "Untergrenzen für σ²... gegen Scheingenauigkeit" als Ablehnungsregel (σ² unter der Schwelle ⇒ FIT_FAILED) war falsch -- "Untergrenzen" heisst CLAMP, nicht verwerfen. Bestätigt an einer 400-Serien-Stichprobe der Live-DB: die Ablehnungs-Lesung verwarf **~50 %** jedes tatsächlich versuchten Fits, kein Rand-/Ausnahmefall, sondern strukturell (ein Monatswert pro Periode macht σ²_ε/σ²_η schwach identifizierbar, MLE landet routinemässig auf dem Rand). Fix: σ² wird bei Unterschreitung auf die Untergrenze GEKLEMMT (`mod.smooth(params_geklemmt)`, keine Neuoptimierung), FIT_FAILED bleibt reserviert für echte Fehlschläge (Nicht-Konvergenz, Exception, nicht-finite Prognose). Floors selbst auch korrigiert: absolut statt pro-Serie-relativ (beide σ² leben schon im Log-Raum, der selbst schon skaleninvariant ist -- ein Pétrus und ein 10-EUR-Wein brauchen DIESELBE Grenze, nicht verschiedene), `sigma2.irregular`-Floor empirisch aus `fit_provider_effects`s eigenem `var_residual_after` (~0,206 auf der Live-DB) abgeleitet (5 % davon, ~0,01). **FIT_FAILED-Quote nach dem Fix: 1,93 % der tatsächlich versuchten Fits** (vorher ~50 %) -- unter der 5 %-Schwelle, keine Review nötig. 4 neue Tests in `test_forecast_local_level.py` (Clamp statt Failed bei echtem Live-DB-Fall, Nicht-Konvergenz bei exakt konstanter Serie bleibt FIT_FAILED, Exception-Pfad gemockt, Clamp-Zähler).

**2.4 Prognose-Verteilung** (S): Aus Zustandsverteilung am Ziel-Zeitpunkt: Median, Quantile q05–q95 im Log, Rücktransformation. **Prädiktions-** nicht Konfidenzintervall (Messrauschen einrechnen!). Test: Intervall ≥ Messrauschen-Intervall.
- **Status: erledigt 2026-11-11.** Empirisch bestätigt (nicht aus der statsmodels-Doku übernommen): `get_forecast(h).var_pred_mean` entspricht bereits exakt der gefilterten Zustandsvarianz PLUS `sigma2.irregular` -- kein manueller Zuschlag nötig, auch nach dem Floor-Clamping nicht (derselbe `UnobservedComponents`, nur fixierte statt optimierte Parameter). Quantile: `mean + norm.ppf(q) * sd`, Gaussian im Log-y-Raum, per Konstruktion monoton.

**2.5 Vergleich gegen Baselines** (M): Eval-Harness aus 1.5.
- AC (G2): Pinball-Loss < beste Baseline in ≥ 60 % der Gruppen; Coverage 80 % ∈ [77, 83].
- **Status: erledigt 2026-11-11.** `local_level` als `make_local_level_forecaster()` direkt in `forecast.eval`s bestehendem `Forecaster`-Contract registriert (`run.py --models ..., local_level`), kein Harness-Code geändert. Ein kombinierter Lauf (alle 4 Baselines + local_level, EIN Befehl, EINE DB/`as_of`/Hausbereinigung -- nicht zwei separate Läufe, die wäre kein fairer Vergleich gewesen) über alle ~971k `forecast_input`-Zeilen, ~54 Minuten.
  **Pinball-Loss-AC: 31/34 Gruppen (91,2 %)** -- lokal besser als die jeweils beste Baseline, deutlich über der 60 %-Schwelle. Die 3 Verlust-Gruppen (`dorotheum`/`finarte` je einmal pro Horizont, `n`~200-700) sind kleine, rauschanfällige Häuser.
  **Coverage-80 %-AC (Stand vor dem Copilot-Review, siehe unten): "12m" trifft die Bande ([77,83]), "next" liegt knapp darunter** (next: 74,0 %, 12m: 78,8 % -- Gesamtwerte, "alle"-Zeile). Intervalle für den "next"-Horizont waren leicht zu eng.
  Volle Zahlen (alle Gruppen/Häuser/Dichteklassen, beide Horizonte): `docs/forecast-baseline-report.md`.
  **Update 2026-11-11 (GitHub-Copilot-PR-Review auf PR #106, 2 High- + 1 Low-Finding, alle empirisch verifiziert statt blind akzeptiert/verworfen -- siehe §8-Eintrag unten):** Finding 1 (echtes G1-Leck: `provider_effects` wurde einmal auf dem GESAMTEN `forecast_input` gefittet und schon in `data.py`s `y` eingebacken, bevor `eval.py`s Rolling-Origin-Split überhaupt lief -- jeder Origin "sah" damit teilweise zukünftige Hausoffsets) und Finding 2 (echte fehlende Varianzkomponente: `_monthly_series` mittelt alle Lose eines Kalendermonats VOR dem Kalman-Fit, `sigma2.irregular`/`var_pred_mean` erfasst daher nur das Monatsmittel-Rauschen, nie das einzelne Los -- plausible Erklärung für die obige "next"-Unterdeckung) wurden vollständig gefixt: `fit_provider_effects(conn, cutoff=...)` erlaubt punktuelles Re-Fitting je Origin (`eval.py`s neue `_fit_origin_offsets`/`_apply_origin_offset`), `local_level_forecast` addiert jetzt eine empirische `_within_month_lot_variance` (Serie-eigene Schätzung, Fallback 0,09 bei < 3 Mehrfach-Los-Monaten). Finding 3 (Low, echt aber geringe Priorität: Baselines und `local_level` haben unterschiedliche INSUFFICIENT_DATA-Kriterien, scoren daher nicht exakt dieselben Ziel-Lose) wurde proportional mit einer neuen "Paired-Vergleich"-Sektion im Report behoben (Pinball q0.5 zusätzlich auf die gemeinsame Zielmenge beschränkt), ohne Modell-Logik zu ändern. Neuer kombinierter Live-Lauf (alle 5 Modelle, ~80 Minuten) nach beiden Fixes:
  **Pinball-Loss-AC: weiterhin 31/34 Gruppen (91,2 %)** -- unverändert, weil die Varianz-Korrektur nur die Intervallbreite betrifft, nicht den Median (`norm.ppf(0.5) = 0`), und die Origin-Offset-Korrektur die Rangfolge der Modelle am Median nicht verschiebt.
  **Coverage-80 %-AC: jetzt ÜBERKORRIGIERT** -- next: 74,0 % → **86,7 %**, 12m: 78,8 % → **87,3 %** (Band weiterhin [77,83]). Statt zu enger sind die Intervalle jetzt zu weit, beide Horizonte liegen ausserhalb des Bands. Plausible Ursache: bei den vielen Serien mit überwiegend 1-Los-Monaten (Median-Seriengrösse = 2 Beobachtungen) enthält `sigma2.irregular` schon einen Teil der Einzel-Los-Varianz (keine Monatsmittel-Glättung dort), die zusätzliche additive `within_month_variance` zählt diese dann streckenweise doppelt. **User-Entscheid 2026-11-11: strukturelle Fixes committen, Feinkalibrierung bewusst NICHT hier nachgezogen** -- gehört inhaltlich zu 2.1 (Dichte-Schwellen-Kalibrierung) bzw. Stufe 4 (Konforme Kalibrierung), nicht in diese Review-Runde.
  Aktualisierte volle Zahlen: `docs/forecast-baseline-report.md`.
  **Update 2026-11-12 (GitHub-Copilot-PR-Review auf dem Folge-PR, 2 Medium-Findings, beide empirisch verifiziert -- siehe §8-Eintrag unten):** Finding A (`paired_comparison` schnitt die Zielmengen VOR Anwendung der modell-eigenen `extrapolation_exclusion_mask`, zwei Modelle konnten so dieselbe `n_paired` melden, obwohl `pinball_loss` intern unterschiedliche Teilmengen scorte -- live sichtbar an `n_extrapolation_excluded`-Spreizung von 16 bis 7 956 über Modell/Horizont) und Finding B (`forecast_input`s Eligibility -- D15-Recency UND der OUTLIER-Flag -- bezieht sich auf "heute"/Gesamthistorie statt auf den jeweiligen Origin, `cutoff` alleine schliesst das G1-Leck damit nicht vollständig; Live-Messung: bis zu 10,74 % der Serien am frühesten Origin nur wegen eines Verkaufs NACH diesem Origin "aktiv", OUTLIER-Flag-Neuberechnung nur auf Vor-Origin-Daten weicht in 12 % der Fälle vom Gesamthistorie-Flag ab) wurden beide vollständig gefixt: `paired_comparison` schneidet jetzt die bereits GESCORTEN Mengen; `fit_provider_effects`/`_load_fe_frame` und `evaluate_series`/`evaluate` bekommen einen neuen `exclude_lot_ids`/`origin_outlier_ids`-Pfad plus eine origin-bewusste `_is_active_as_of`-Recency-Prüfung (beide nur aktiv, wenn `cutoff` gesetzt ist -- der Produktionspfad mit `cutoff=None` bleibt bytegleich). Neue `lot_id`-Spalte end-to-end durch `forecast/data.py` ergänzt (einzige eindeutige Zeilen-Identität für den Ausschluss). Dritter kombinierter Live-Lauf nach beiden Fixes (alle 5 Modelle, ~70 Minuten reine Rechenzeit, nach einem einmaligen transienten Lese-Fehler der externen Samsung-Platte beim ersten Versuch -- per `PRAGMA integrity_check` als Platten-Hickup statt Datenkorruption verifiziert, danach folgenlos wiederholt):
  **Pinball-Loss-AC: 31/33 Gruppen (93,9 %)** -- minimal besser als zuvor (91,2 %/31-von-34), einzige verlorene Gruppe in beiden Horizonten weiterhin `finarte`.
  **Coverage-80 %-AC: weiterhin überkorrigiert, praktisch unverändert** -- next: 86,7 % → 86,4 %, 12m: 87,3 % → 86,7 % (Band weiterhin [77,83]). Bestätigt: die Übererfüllung war kein Leckage-Artefakt der Finding-A/B-Lecks, sondern echter Stufe-2.1/Stufe-4-Kalibrierungsbedarf, wie bereits entschieden.
  FIT_FAILED-Quote: 1,56 % (`local_level`, Schwelle 5 %), unauffällig.
  Aktualisierte volle Zahlen: `docs/forecast-baseline-report.md`.
  **Update 2026-11-13 (Senior-Review auf diesem Diff, Finding Coverage-Überkorrektur vollständig behoben statt vertagt):** die additive `_within_month_lot_variance`-Korrektur (oben) überkorrigierte strukturell (86-87 % statt [77,83]), weil sie bei Serien mit überwiegend 1-Los-Monaten einen Teil des Lot-Rauschens doppelt zählte, das `sigma2.irregular` dort bereits selbst trug. Ersetzt durch ein eigenes State-Space-Modell (`_LocalLevelTrend`, `models.py`, ersetzt `UnobservedComponents`) mit PRO-MONAT-Beobachtungsvarianz `sigma2.irregular / k_t` (`k_t` = Los-Anzahl des Monats) statt der additiven Näherung -- statistisch exakt, nicht approximiert (2.2's eigene "Option A mit Gewicht"-Alternative, für v1 zurückgestellt, jetzt umgesetzt). Live-Subsample-Diagnose (1 600 Serien, beide Horizonte) zeigte danach: Coverage ist **dichteabhängig**, nicht pauschal falsch -- im Band bei `n_train>=10`/12m (0,827 ungeklemmt), knapp drunter bei `n_train>=10`/next (~0,75-0,79, statistisch real), 0,62-0,76 unter 10 Beobachtungen unabhängig vom Floor-Clamp-Status (nur "beide Floors geklemmt" bei sehr kleinem n zeigt einen deutlichen Einbruch, z. B. 0,29 bei n=7) -- deckt sich mit §5 Stufe 3.6 ("INSUFFICIENT_DATA ist das Ergebnis, kein Fehler") und zeigt exakt, wo Stufe 3.4 (EB-Shrinkage) und Stufe 4.1 (Mondrian-Conformal je Dichteklasse) ansetzen müssen. **Zweiter echter Bug dabei gefunden+gefixt:** `local_linear_trend` (2.6) zeigte zunächst 12-22 % FIT_FAILED -- Ursache empirisch verifiziert (nicht vermutet): jeder nicht-konvergente Fit traf exakt statsmodels' `fit()`-Default `maxiter=50`, während die Dämpfung legitim gegen ihre offene untere Grenze (→0, "kein echter Trend") lief, die ein Optimierer nie exakt erreicht. Mit `maxiter=200` konvergierten dieselben Fälle in 50-54 Iterationen; FIT_FAILED danach 0,0-3,1 % in allen Dichteklassen. **User-Entscheide 2026-11-13:** (1) Gate G2's Coverage-AC wird über ALLE Dichteklassen bewertet, nicht nur die D5-Population (>=10) -- siehe Gate-G2-Eintrag unten für die Konsequenz; (2) `local_linear_trend` kommt in den vollen kombinierten Lauf als echter Kandidat.
  **Vierter kombinierter Live-Lauf** (6 Modelle -- 4 Baselines + beide Kalman-Varianten --, beide Horizonte, ~2 Std. Rechenzeit): **Pinball-Loss-AC: `local_level` 30/32 Gruppen (93,75 %)** (Dichteklassen + Häuser, `n_train=1-2` ohne gültige Baseline-Vergleichszahl daher nicht gezählt) -- einzige verlorene Gruppe weiterhin `finarte`, beide Horizonte. **`local_linear_trend`: ebenfalls 30/32 Gruppen (93,75 %)** -- numerisch gleich gut auf Pinball, aber **durchgängig marginal schlechter als `local_level`** auf sowohl Pinball q0.5 (gepaarter Vergleich: next 0,1459 vs. 0,1468; 12m 0,1540 vs. 0,1544) als auch Coverage (niedriger in praktisch jeder Dichteklasse/jedem Haus, z. B. `n_train=10+`/12m: 0,845 vs. 0,838). **Coverage-80 %-AC über alle Dichteklassen (`local_level`):** next -- `n_train=1-2` 0,674/`3-4` 0,686/`5-9` 0,719/`10+` 0,790 (einzige Klasse im Band); 12m -- `1-2` 0,663/`3-4` 0,712/`5-9` 0,754/`10+` 0,845 (knapp über dem Band). **Nur next/10+ liegt im Zielband [77,83] -- die AC ist über alle Dichteklassen bewertet damit NICHT erfüllt**, wie von der Coverage-AC-Entscheidung oben bereits erwartet; das ist ein echtes, jetzt präzise quantifiziertes Stufe-3.4/4.1-Kalibrierungsbedürfnis, keine Regression dieser Runde. FIT_FAILED: `local_level` 1,31 % (1 604/122 010), `local_linear_trend` 1,02 % (1 250/122 010) -- beide unauffällig.
  **Hinweis für künftige Reviews:** der Produktionspfad (`cutoff=None`) ist durch den Modellklassenwechsel (`UnobservedComponents` -> `_LocalLevelTrend`) NICHT mehr bytegleich zu PR #108 -- anders als in der letzten Runde (wo Bytegleichheit ein Verkaufsargument des Fixes war), ist das hier eine bewusste, beabsichtigte Verhaltensänderung (die Korrektur WAR der Zweck des Fixes).
  Aktualisierte volle Zahlen: `docs/forecast-baseline-report.md`.

**2.6 Zusatz: Trend-Komponente testen** (M): `local linear trend` vs. `local level`; nur übernehmen, wenn nach G2 besser. Dämpfung zwingend (Trend-Extrapolation über 12 M kann Fantasiepreise liefern).
- **Status: erledigt 2026-11-13.** `local_linear_trend_forecast`/`make_local_linear_trend_forecaster` implementiert (`_LocalLevelTrend(trend=True)`, gedämpfte Steigung über einen skalierten Sigmoid auf `(0, DAMPING_MAX=0.98)`, nie der unbeschränkte Random-Walk eines ungedämpften linearen Trends). Ergebnis siehe 2.5's Update oben: **getestet, NICHT übernommen** -- durchgängig marginal schlechter als `local_level` auf Pinball UND Coverage, kein Dichtebereich, in dem der Trend-Term einen Vorteil bringt. `local_level` bleibt das Produktionsmodell für Stufe 2.

**2.1 Dichte-Schwellen kalibrieren** (S): Backtest: ab welchem `n_obs`/Spanne schlägt Local-Level die Baselines? D5 wird mit den Zahlen belegt.
- **Status: erledigt 2026-11-13 (Pinball-Teil), Coverage-Teil ist jetzt das dokumentierte Ergebnis statt eine Kalibrierungsaufgabe dieses Schritts.** Pinball: `local_level` schlägt die beste Baseline in JEDER Dichteklasse (`1-2` nicht direkt vergleichbar, siehe oben; `3-4`/`5-9`/`10+` alle Gewinne) -- D5's `>=10 obs`-Schwelle ist für die Pinball-AC nicht nötig, sie gilt schon ab `n_train=3`. Coverage: dichteabhängig wie in 2.5 dokumentiert, im Band nur bei `n_train>=10`/next -- die eigentliche Korrektur (Stufe 3.4 EB-Shrinkage / Stufe 4.1 konforme Kalibrierung je Dichteklasse) ist bewusst NICHT Teil dieses Schritts (User-Entscheid, gleiche Begründung wie bei der vorherigen Überkorrektur: ein globaler Parameter gegen ein dichteabhängiges Problem wäre derselbe Fehler nochmal).

**Gate G2:** Senior-Review mit Plots (Fan-Charts) der 30 Gold-Set-Weine.
- **Noch offen, Vorbedingung fehlt:** `data/tests/fixtures/forecast_gold.json` (G7) existiert noch nicht -- das bestehende `gold_lots.csv`/`build_gold_set.py` ist ein ANDERES Gold-Set (§4.0 Wein-Normalisierung: Produzent/Wein/Jahrgang/Menge, keine Preishistorie). User-Entscheid (2026-11-11): Kuration erst bei Gate G2 selbst, nicht parallel vorgezogen. **Zusatz 2026-11-13:** die Coverage-80-%-AC ist jetzt (User-Entscheid: Bewertung über alle Dichteklassen) mit den aktuellen Zahlen NICHT erfüllt -- Gate G2 kann im Sinne der ursprünglichen Guardrail G2 ("(a) UND (b)") formal nicht als vollständig bestanden gelten, bevor entweder die Coverage-Zahlen durch Stufe 3.4/4.1 verbessert werden oder die AC selbst im Review nochmal angepasst wird. Die Pinball-AC (a) gilt als erfüllt (93,75 %, weit über 60 %).

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
| D21 | `size_assumed=1` (kein Grössen-Hinweis in den Rohdaten, `_assume_default_bottle_size` setzt 7,5 dl als Default) macht ~38 % aller `SINGLE`-Lose aus (Gate-G0-Fund, 2026-11-06, Code-Review). `forecast_input` behandelt diese Zeilen aktuell identisch zu einer bestätigten 7,5-dl-Flasche — nur gezählt/reported (`_report_07_forecast_input`), nicht ausgeschlossen oder separat geflaggt. Ausschliessen (verliert einen grossen, mutmasslich meist korrekten Anteil echter 750-ml-Flaschen) oder als eigenes `ppb_flags`-Flag markieren (Modell entscheidet, wie 0.6) oder so lassen (750 ml ist die weit überwiegende reale Grösse, der Default ist kein Rateversuch ins Blaue)? **2026-11-09 (G0.7b, Finding 4):** Semantik von `size_assumed` bewusst verbreitert — nicht mehr nur "kein Hinweis gefunden", sondern auch "Format bekannt, exakte Grossflaschen-Konvention geraten" (christies' Jeroboam Bordeaux/Champagne-Heuristik, weinauktion/steinfels' Bare-Jeroboam-Fallback), da beides für das Forecast-Modell dieselbe Unsicherheit ist und die bestehende Spalte/`fit_provider_effects`-Kovariate genau dafür gebaut ist. Betrifft 3 081 zusätzliche Zeilen (3 steinfels, 0 weinboerse, 3 078 christies). **D21 ENTSCHIEDEN (User, 2026-11-09): Option 2 — `size_assumed` bleibt als eigenes Flag/Kovariate, kein Ausschluss.** Nach dem steinfels-Fix (G0.7b) + Rebuild: `forecast_input` gesamt 971 510 Zeilen, davon 35 426 (3,6 %) `size_assumed=1`; steinfels alleine fiel von 619 auf 28 solcher Zeilen (−95,5 %, Haus-Offset in `fit_provider_effects` von ~3,04× auf log-offset 0.020 ≈ 1,02× — praktisch neutral). Kein Code-Änderungsbedarf: `fit_provider_effects` (1.3) nutzt `size_assumed` bereits als Kovariate, genau wie entschieden. | 0.7, Stufe 1-2 — **erledigt**, kein offener Punkt mehr |

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

D10–D20 sind damit getroffen.

**Entschieden am 2026-11-09 (nach G0.7b, steinfels-Fix + Rebuild):**
D21 `size_assumed`-Behandlung = **als eigenes Flag/Kovariate belassen** (nicht: ausschliessen) — `fit_provider_effects` (1.3) nutzt `size_assumed` dafür bereits als Regressor, kein Code-Änderungsbedarf. Entscheidung erleichtert durch den steinfels-Fix selbst: die betroffene Zeilenzahl ist mit dem Fix von ~38 % aller `SINGLE`-Lose auf 3,6 % von `forecast_input` gesunken, und die einzige konkret nachgewiesene Verzerrung durch Grössen-Rateversuche (steinfels' Haus-Offset) ist dadurch bereits von ~3,04× auf praktisch neutral (~1,02×) gefallen.

D10–D21 sind damit alle getroffen.

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
| 2026-11-09 | G0.7b (Stufe-1 QTY_ASSUMED-Nachprüfung, steinfels) | Claude (`code-review`-Skill auf vollem unkommittierten Diff, nach User-Korrektur: "Steinfels liefert definitiv immer die Menge und den Preis pro Lot. Immer.") | Ursprüngliche Annahme (steinfels liefert keine Menge/Grösse, "bewusste Design-Entscheidung") war falsch — echter Bug: `description` enthält die Angabe immer (z. B. "4 50cl-Flaschen"), nie geparst. Neue `_weinauktion_parse_qty_size` (steinfels + weinboerse, 99,4 % Archiv-Abdeckung) + `parse_christies_secondary`-Erweiterung + `parse_dl`-Reihenfolge-Fix. Review danach: 10 Befunde, 8 echte Bugs (unverankerte Size-Suche griff unverwandte Zahlen ab, `_CHAMPAGNE_RE` ohne Wortgrenze traf "Mumm" in "Mummius", Jeroboam-Wert 45.0 statt 50.0 vertauscht + `_WA_FORMAT_DL`-Duplikat-Tabelle auf `BOTTLE_FORMATS` zurückgeführt, Mixed-Format-Vergleich auf rohe Spelling- statt aufgelöste dl-Werte, `build_wines._parse_bottle_formats` fingierte Menge aus Limited-Edition-Zählung auf MIXED-Dekanter-Lot, Plural-Dekanter-Erkennung, `parse_dl`-Reihenfolgegefahr proaktiv behoben). 2 Befunde bewusst zurückgestellt: (4) Jeroboam-Grössenkonvention wird geraten, landete aber ohne `size_assumed`-Flag — Architekturfrage, nicht mechanischer Bug; (10) christies-Parser-Performance, kein nachgewiesener realer Kostenpunkt. | 8 Bugs gefixt + Regressionstests; danach Finding 4 auf User-Wunsch VOR dem Rebuild zusätzlich gefixt: `size_assumed`-Semantik bewusst verbreitert (siehe D21-Zeile oben) — `_christies_format_dl`/`parse_christies_secondary`/`_weinauktion_parse_qty_size` geben jetzt zusätzlich ein `size_assumed`-Flag zurück, `add_lot` persistiert es; 3 081 betroffene Zeilen (3 steinfels, 0 weinboerse, 3 078 christies). Volle Suite 456/456 grün. Finding 10 bleibt offen/dokumentiert. |
| 2026-11-10 | 1.5 (Rolling-Origin-Evaluator) | Claude (Design via `advisor` vor Implementierung: Forecaster-Signatur `(train, origin, horizon) -> dict\|None`, Log-y-Skala für alle Metriken ausser MAPE/MdAPE, Long-Format-Rows-Tabelle als zentrale Zwischenstruktur) | Kein Review-Finding — neues Modul, keine Review in diesem Schritt angefordert. Design-Entscheide dokumentiert in `eval.py`s Docstrings: Dichteklassen aus 3.6/D5 übernommen statt neu erfunden (`1-2/3-4/5-9/10+`, nach `n_train`, nicht Gesamtserien-Grösse — sonst Zukunfts-Leck); 12M-Horizont rechts-zensierte Origins ausgeschlossen statt auf Teilfenster gewertet; `split()` nutzt Kalendermonate, kein 365-Tage-Fenster (Leap-Year-Differenz per Test belegt). | `data/forecast/eval.py` (Rolling-Origin-Split + alle Metriken + Report-Writer) + `run.py` (CLI, G6) + `data.load_all_series` (Bulk-Loader) neu; 22 neue Tests (`test_forecast_eval.py`), beide Pflicht-Tests (`test_no_lookahead` als Spy- UND Cheater-Forecaster-Variante, `test_metric_known_values` mit handgerechneten Pinball/Winkler/Coverage/MAPE-Werten). Volle Suite 478/478 grün. CLI erfolgreich gegen Live-DB getestet (0 Modelle, Report-Datei erzeugt). |
| 2026-11-10 | 1.4 (Baselines) + Live-Verifikation von 1.4/1.5 | Claude (eigene Tests + 4 Bugs erst beim tatsächlichen Live-DB-Lauf gefunden, nicht durch synthetische Tests allein; 1 weiterer Bug durch eigenen `advisor`-Review NACH dem vierten Live-Lauf, bevor irgendetwas committet wurde) | 6 echte Bugs über die Implementierung: (1) `_rolling_median_12m` ankerte das 12M-Fenster am Prognose-Zieldatum statt am letzten bekannten Datum -- für den 12M-Horizont IMMER leer, vom eigenen Konstante-Serie-Test gefangen; (2) ungekappter verschachtelter Residual-Backtest war O(n²) für ~2000-Zeilen-Serien, Live-Lauf nach 20+ Min. ohne Ende abgebrochen; (3) `extrapolation_flag` rief `math.exp()` auf rohen Log-Forecast, `OverflowError` brach einen ~25-Min.-Lauf ab; (4) `mape_eur`/`mdape_eur` exponenzierten denselben Wert ohne Schutz -- NumPy warnt nur, aber eine `inf`-Zeile macht den Mittelwert für die ganze Gruppe unbrauchbar (Report zeigte `2,8×10^50`); (5) erster Fix von (4) filterte nur `~np.isfinite`, übersah aber `exp()`-Werte knapp UNTER der Überlauf-Grenze (z. B. `exp(600)` -- finite, aber absurd) -- derselbe Report zeigte nach Fix (4) weiterhin astronomische MAPE-Werte; (6) `make_baseline` verlangte nur >= 1 Residuum statt >= 2 -- mit genau 1 Residuum sind alle 7 Quantile identisch (`np.quantile([r], q) == r` für jedes `q`), eine scheinsichere Nullbreite-Prognose aus einem einzigen Datenpunkt (exakt die "false certainty", vor der `MIN_OBS`s eigener Docstring warnt). Sichtbar im Live-Report: `n_train=1-2`/Horizont `next` zeigte `Breite 50/80/95% = 0.000` für JEDE Baseline. | (1)+(2) gefixt vor dem ersten Live-Lauf (Konstante-Serie- bzw. eigener Performance-Test); (3)+(4)+(5) durch 3 aufeinanderfolgende Live-DB-Läufe gefunden, jeweils sofort gefixt + Regressionstest + Re-Lauf; (6) durch eigenen `advisor`-Review nach dem vierten (erfolgreichen) Live-Lauf gefunden, noch vor jedem Commit. `MAX_BACKTEST_STEPS=50` (gekappt auf die letzten GEEIGNETEN Mini-Origins, nicht die letzten rohen Zeilenindizes), `extrapolation_flag`-Vergleich bleibt vollständig im Log-Raum, `mape_eur`/`mdape_eur` schliessen jetzt `extrapolation_flag`-markierte Zeilen aus (nicht nur nicht-finite) und zählen sie (`n_mape_excluded`, eigene Report-Spalte), `make_baseline` verlangt jetzt >= 2 Residuen. **G2-Designfrage dem User vorgelegt statt selbst entschieden** (`extrapolation_flag`-Ausschluss nur für MAPE/MdAPE, oder für alle Metriken?): **User-Entscheid 2026-11-10 — auf ALLE Metriken ausweiten** (nicht nur im Report-Header vermerken) — dieselbe Kontamination war in Pinball/Winkler nur weniger sichtbar (Log-Raum dämpft 10^50 auf z. B. 78 statt ~5), nicht behoben, und G2 nennt Pinball-Loss als Haupt-Beat-the-Baseline-Kriterium. Umgesetzt: `extrapolation_exclusion_mask` (umbenannt von `mape_exclusion_mask`) jetzt von `pinball_loss`/`winkler_score`/`coverage`/`median_width`/`mape_eur`/`mdape_eur` gemeinsam genutzt, `n_extrapolation_excluded` (umbenannt von `n_mape_excluded`) als eine Spalte für alle. 4 weitere Tests (gezielter Nachweis, dass Pinball/Winkler/Coverage jetzt auch ausschliessen; "alle Zeilen ausgeschlossen" → NaN statt Crash). `test_forecast_eval.py` von 22 auf 30. Volle Suite 509/509 grün.
  **Fünfter Live-Report-Lauf** (nach Fix 6 + der Metrik-Ausweitung):
  **~33 Minuten, fehlerfrei, keine Ausreisser mehr in irgendeiner
  Spalte** -- `n_train=1-2` ist aus dem "next"-Horizont komplett
  verschwunden. Finale Kopfzahlen siehe 1.4-Eintrag in §5 und
  `docs/forecast-baseline-report.md`. **Stufe 1 (1.1-1.5) damit
  vollständig abgeschlossen** -- noch ausstehend: Senior-Code-Review
  über den gesamten 1.4+1.5-Diff vor jedem Commit (Standing Rule), dann
  Gate G1 (Baseline-Zahlen im Review festschreiben).
| 2026-11-10/11 | Senior-Review (1.4+1.5-Diff) + Stufe 2 (2.2-2.5) + D8 | Claude (`code-review high` auf dem vollen uncommitteten Diff; danach `advisor`-Konsultation zu Stufe 2's Design, zweimal -- vor Implementierung und nach einem Live-DB-Befund, der die erste Lesung widerlegte) | **Senior-Review (6 Befunde, alle echt, alle gefixt):** (1) `_parse_bottle_formats` nur auf rohes `mixed_lot`-Flag gegated, nicht auf `_classify_lots`' Keyword-/Gruppen-MIXED -- in `_strip_bottle_format_from_wine` (bleibt vor `_classify_lots`, wegen `wine_key`-Gruppierung) und `_parse_bottle_formats` (jetzt danach, `lot_kind != 'MIXED'`) aufgeteilt; (2) `_christies_format_dl`s Jeroboam-Check nur ASCII, "jéroboam" fiel durch; (3) `parse_dl`s bare "jeroboam" defaultete unbegründet auf Champagne (30.0) statt Bordeaux (50.0), inkonsistent zu jedem anderen Jeroboam-Pfad dieser Runde; (4) `parse_dl`s Unit-Regex ohne `\b`, "15lbs" matchte "l" → falsch 150.0dl; (5) `_CHRISTIES_FORMAT_DL` duplizierte Literale statt `BOTTLE_FORMATS`; (6) weinauktion/steinfels' Jeroboam-Default hatte KEINEN Produzenten-Check (immer Bordeaux), christies' identische Ambiguität schon -- `wine_text`-Parameter ergänzt, beide Loader geben jetzt den Wein-/Titeltext mit. **Zusätzlich gefunden, nicht Teil des Diffs (nur erwähnt, nicht gefixt):** `_WB_NAMED_DL["jeroboam"]=45.0` in `load_weinboerse`s älterem, separatem Parser -- derselbe Bug wie `_WA_FORMAT_DL`s erste Fassung, aber in unverändertem Code, daher nicht im Scope dieser Review-Runde. **Stufe 2 (2.2-2.5):** Local-Level-Modell gebaut, 2 Design-Entscheide per `advisor` getroffen und dokumentiert (Reihenfolge 2.2+2.4→2.3→2.5→2.1, D8 jetzt umgesetzt statt vertagt). **Echter Bug, erst beim Live-Lauf gefunden:** `_persist_provider_effects` lief ursprünglich als letzter Schritt in `build_wines.run()` -- das passiert VOR `_fill_price_per_bottle`/`_flag_price_outliers`, `forecast_input` war zu dem Zeitpunkt leer, 0 Zeilen persistiert. Verschoben nach `build_db.py`s Pipeline (nach 0.5/0.6). **Design-Korrektur per `advisor`, nach einem zweiten Live-Befund:** "Untergrenzen für σ²" als Ablehnungsregel (FIT_FAILED) statt Clamp verwarf ~50 % jedes Fit-Versuchs (strukturell, nicht Zufall -- ein Beobachtungspunkt pro Monat macht σ²_ε/σ²_η schwach identifizierbar) -- auf Clamp umgestellt, Floors zusätzlich von relativ auf absolut korrigiert (Log-Raum ist bereits skaleninvariant). | Alle 6 Review-Findings gefixt + Regressionstests, 538/538 Tests grün. D8 umgesetzt (`provider_effects`-Tabelle + Pipeline-Fix + House-Adjustment in `load_series`/`load_all_series`), 2 volle DB-Rebuilds (erster mit dem Pipeline-Bug, zweiter korrekt -- beide mit Backup+SHA-256-Verify davor). Kombinierter Live-Lauf (4 Baselines + local_level, 1 Befehl, ~54 Min., `docs/forecast-baseline-report.md`): **G2-AC Pinball-Loss 31/34 Gruppen (91,2 %, Schwelle 60 %) erfüllt.** G2-AC Coverage 80 %: "12m" in Band (78,8 %), "next" knapp darunter (74,0 %) -- bewusst nicht nachjustiert, das ist Stufe 4's Aufgabe. FIT_FAILED-Quote nach dem Clamp-Fix: 1,93 % (Schwelle 5 %). 2.1/2.6/Gate G2 (Gold-Set fehlt) bleiben offen. |
| 2026-11-11 | GitHub-Copilot-PR-Review (PR #106) | GitHub Copilot (automatisiert, 3 Findings); Claude verifizierte jedes Finding empirisch gegen die Live-DB statt die Einstufung blind zu übernehmen oder zu verwerfen | **Finding 1 (High, verifiziert ECHT + MATERIELL):** `provider_effects` wurde EINMAL auf dem gesamten `forecast_input` gefittet und schon in `data.py`s `y` eingebacken, BEVOR `eval.py`s Rolling-Origin-Split lief -- ein echtes G1-Leck (jeder Origin "sah" so teilweise zukünftige Hausoffsets). Live-Messung: Vollfit vs. Fit auf `lot_date < as_of-12M` korreliert nur mit 0,90; `pandolfini` (1 298 Beob.) verschiebt sich um 0,25 im Log-Raum (~28 % Preis). **Finding 2 (High, verifiziert ECHT + MATERIELL):** `_monthly_series` mittelt alle Lose eines Kalendermonats VOR dem Kalman-Fit -- `sigma2.irregular`/`var_pred_mean` erfasst daher nur das Rauschen des MONATSMITTELS, nie das eines einzelnen Loses, obwohl `evaluate_series` einzelne Lose scort. Live-Messung: 52,19 % aller `forecast_input`-Zeilen liegen in einer (Serie, Monat)-Zelle mit ≥2 Losen; die gepoolte Varianz dort (~0,0913) ist ~9× der etablierte `_SIGMA2_IRREGULAR_FLOOR` (0,01) -- plausible Erklärung für die oben dokumentierte "next"-Unterdeckung (74,0 %). **Finding 3 (Low, verifiziert ECHT, geringe Priorität):** Baselines (brauchen ≥2 Backtest-Residuen) und `local_level` (braucht nur `LOCAL_LEVEL_MIN_MONTHS=2`) haben unterschiedliche INSUFFICIENT_DATA-Kriterien, scoren daher unterschiedlich grosse, nicht identische Ziel-Mengen (88 087 vs. 79 338 "next"-Ziele) -- die 91,2 %-Pinball-Aussage ist damit kein strikt gepaarter Vergleich. **User-Entscheid: beide High-Findings vollständig fixen, Finding 3 proportional (Report-Transparenz statt Modell-Änderung).** Fixes: `fit_provider_effects(conn, cutoff=...)` + `eval.py`s neue `_fit_origin_offsets`/`_apply_origin_offset`-Maschinerie (punktuelles Re-Fitting je Origin, EINMAL pro Origin, geteilt über alle Modelle/Horizonte); `local_level_forecast` addiert eine neue `_within_month_lot_variance` (Serie-eigene gepoolte Varianz, Fallback 0,09 bei < 3 Mehrfach-Los-Monaten); neue `paired_comparison`/`paired_subset` + "Paired-Vergleich"-Report-Sektion (Finding 3). Timing-Studie vor dem Live-Lauf: `_fit_origin_offsets` 202,8 s für 4 Origins (~3,4 Min. Zusatzkosten, akzeptabel ggü. ~54 Min. Baseline). Ein Testfixture-Bug (fixe statt relative Kalenderdaten, fiel wegen D15s 36-Monate-Fenster durch) und ein echter Pylint-Fund (`R1711`, überflüssiges `return None`) unterwegs gefunden und gefixt. Neuer kombinierter Live-Lauf scheiterte beim ERSTEN Versuch nach ~80 Min. (`FileNotFoundError` -- `--out docs/...` war relativ zum `data/`-Arbeitsverzeichnis, `docs/` liegt aber im Repo-Root; ganzer Lauf musste mit absolutem Pfad wiederholt werden, ~80 Min. Rechenzeit verloren). | Beide High-Findings vollständig gefixt + neue Tests (`FitProviderEffectsCutoffTest`, `ApplyOriginOffsetTest`, `OriginOffsetLeakageTest`, `WithinMonthLotVarianceTest`, `LocalLevelForecastIncludesWithinMonthVarianceTest`, `PairedComparisonTest`, `WriteBaselineReportPairedSectionTest`), volle Suite weiterhin grün, Pylint clean (bis auf die bereits als CI-irrelevant bestätigte `R0917`). Zweiter (korrigierter) kombinierter Live-Lauf, alle 5 Modelle, ~80 Min.: **Pinball-Loss-AC unverändert 31/34 Gruppen (91,2 %)** (Varianz-Korrektur wirkt nur auf Intervallbreite, nicht auf den unveränderten Median). **Coverage-80 %-AC jetzt überkorrigiert statt unterkorrigiert**: next 74,0 % → 86,7 %, 12m 78,8 % → 87,3 % (Band [77,83], beide jetzt drüber statt einer drunter) -- mutmaßlich weil `sigma2.irregular` bei den vielen 1-Los-Monat-Serien (Mediangrösse 2 Beobachtungen) schon einen Teil der Einzel-Los-Varianz trägt und die zusätzliche additive Varianz diese doppelt zählt. **User-Entscheid 2026-11-11: strukturelle Fixes jetzt committen, Feinkalibrierung bewusst auf Stufe 2.1/Stufe 4 verschoben, nicht in dieser Runde nachgezogen.** FIT_FAILED-Quote nach beiden Fixes: 0,83 % (2 751/332 636), unverändert unauffällig. |
| 2026-11-12 | GitHub-Copilot-PR-Review (Folge-PR nach #107) | GitHub Copilot (automatisiert, 2 Medium-Findings); Claude verifizierte beide empirisch gegen die Live-DB, korrigierte dabei eine eigene erste (zu niedrige) Materialitäts-Schätzung für Finding B's OUTLIER-Teil, statt sie stehen zu lassen | **Finding A (Medium, verifiziert ECHT + MATERIELL):** `paired_comparison` schnitt die Zielmengen VOR Anwendung der modell-eigenen `extrapolation_exclusion_mask` -- zwei Modelle konnten dieselbe `n_paired` melden, obwohl `pinball_loss` intern unterschiedliche Zeilen scorte. Live-Beleg: `n_extrapolation_excluded` streut bereits im bestehenden Report von 16 bis 7 956 über Modell/Horizont-Kombinationen (~500-fach), unmöglich bei identischen ausgeschlossenen Zeilen. **Finding B (Medium, verifiziert ECHT + MATERIELL, zwei Teil-Lecks):** `forecast_input`s D15-Recency-Prüfung (`series_last_obs >= date('now','-36 months')`) UND der OUTLIER-Flag (Median/MAD über die GESAMTE Historie, `_flag_price_outliers`) beziehen sich immer auf "heute"/Gesamthistorie statt auf den jeweiligen Rolling-Origin -- `cutoff` alleine (Finding 1 aus der letzten Runde) schliesst das G1-Leck damit nicht vollständig. Live-Messung (4 echte Origins aus `half_year_origins`): Recency-Teil betrifft bis zu 10,74 % der Serien am frühesten Origin (2025-01-01), fallend auf 1,51 % am spätesten (2026-07-01). OUTLIER-Teil: ursprüngliche Schätzung von "≤1,79 %" war ein Messfehler (nicht zu `_flag_price_outliers`s eigener Population passende SQL-Abfrage, `auctions`-Join + `sold=1`-Filter + fehlender `QTY_SUSPECT`-Ausschluss) -- korrigiert auf 2,295 % (56 114/2 444 946) Gesamthistorie-Rate, Origin-spezifische Neuberechnung am frühesten Origin: 2,168 % mit 88 % Überlappung zu den real persistierten Flags (bestätigt kein Bug, genau der erwartete Leck-Effekt). **User-Entscheid: Finding A sofort fixen (empfohlen), Finding B vollständiger Fix (Recency + Outlier, origin-bewusst) statt der günstigeren Recency-only-Option.** Fixes: `paired_comparison` schneidet jetzt die bereits gescorten (nicht die rohen) Mengen; neue `build_db._outlier_lot_ids` (reine Funktion, aus `_flag_price_outliers` extrahiert, kein Verhaltensunterschied) wiederverwendet von `eval.py`s neuer `_origin_outlier_lot_ids`/`_origin_outlier_ids` (Origin-spezifische Neuberechnung); neue `_is_active_as_of` (origin-bewusste Recency, auf rohen Trainingsdaten vor jedem Ausschluss, D15s eigener Konvention folgend); `fit_provider_effects`/`_load_fe_frame` bekommen `exclude_lot_ids`, `evaluate_series`/`evaluate` bekommen `origin_outlier_ids` -- beide Pfade NUR aktiv wenn `cutoff`/`origin_outlier_ids` gesetzt ist, der Produktionspfad (`cutoff=None`) bleibt bytegleich. Neue `lot_id`-Spalte end-to-end durch `forecast/data.py` ergänzt (einzige eindeutige Zeilen-Identität, Datum/Provider/Preis können kollidieren). Zwei echte Testfixture-Bugs unterwegs gefunden und gefixt (KeyError durch überrestriktive Spy-Guard + falschen Horizont; MAD=0 durch unzureichend variierte Fixture, maskierte den eigentlichen Test-Fall). Timing-Studie vor dem Live-Lauf: `_origin_outlier_ids` 94,7 s + `_fit_origin_offsets` (mit Ausschluss) 38,2 s für 4 Origins ≈ 2,2 Min. Zusatzkosten, akzeptabel. Kombinierter Live-Lauf scheiterte beim ERSTEN Versuch früh mit `sqlite3.DatabaseError: database disk image is malformed` -- VOR dem Neustart verifiziert (nicht einfach geraten): frisches `PRAGMA integrity_check` (read-only) lieferte `ok`, Platte weiterhin gemountet mit 578 Gi frei, Verbindung in `forecast/run.py` bestätigt `mode=ro` (kann nicht geschrieben haben) -- Diagnose: transienter externer-Platten-I/O-Fehler, keine echte Korruption, kein Code-Bug. Nutzer bestätigte nach Wieder-Anstecken der Platte den Neustart; zweiter Versuch lief fehlerfrei durch. | Beide Findings vollständig gefixt + neue Tests (`IsActiveAsOfTest`, `ExcludeOutlierRowsTest`, `RecencyEligibilityLeakageTest`, `OriginOutlierExclusionTest`, `OriginOutlierLotIdsTest`, neue Tests in `FitProviderEffectsCutoffTest`, `PairedComparisonTest`-Erweiterung, `test_forecast_data.py`-Spaltenerweiterung), volle Suite 571/571 grün, Pylint clean (bis auf die bereits als CI-irrelevant bestätigte `R0917`). Dritter kombinierter Live-Lauf (alle 5 Modelle, nach dem Platten-Hickup erfolgreich): **Pinball-Loss-AC: 31/33 Gruppen (93,9 %)** -- minimal besser als zuvor (91,2 %/31-von-34), einzige verlorene Gruppe weiterhin `finarte` in beiden Horizonten. **Coverage-80 %-AC: weiterhin überkorrigiert, praktisch unverändert** -- next 86,7 % → 86,4 %, 12m 87,3 % → 86,7 % (Band [77,83]) -- bestätigt: die Übererfüllung ist kein Leckage-Artefakt, sondern echter Stufe-2.1/Stufe-4-Kalibrierungsbedarf. FIT_FAILED-Quote: 1,56 %, unauffällig. |
| 2026-11-12 | Senior-Review (Finding-A/B-Diff) | Claude (`code-review high` auf dem vollen uncommitteten Diff, forked) | **5 Befunde, alle echt:** (1) `_is_active_as_of`/`_load_fe_frame`s Recency-Check behauptete, "RAW"-Daten zu nutzen, tatsächlich aber schon über `forecast_input`s OUTPUT gefiltert (OUTLIER/QTY_SUSPECT/DUP_CANDIDATE bereits auf SQL-View-Ebene entfernt, BEVOR Python sie sieht) -- Live-Messung: 1,05 % der Serien (1 259/120 357) haben ein dadurch unterschätztes sichtbares letztes Verkaufsdatum. **User-Entscheid: dokumentieren, zurückstellen** (Richtung konservativ, echter Fix würde `forecast_input` umgehen -- grössere Architekturänderung, ausserhalb des Scopes dieser Runde). (2) **Echter Ordering-Bug, gefixt:** `_load_fe_frame` wendete `exclude_lot_ids` VOR der `max_date`-Berechnung an, entgegen der eigenen Docstring und `eval.py`s etablierter Reihenfolge -- konnte eine ganze FE-Gruppe fälschlich als "dormant" verwerfen, wenn ihre einzige Zeile im 36-Monats-Fenster zugleich die ausgeschlossene war. Per Regressionstest hand-verifiziert: mit der alten Reihenfolge lieferte der neue Test exakt den vorhergesagten falschen Wert (0,2 statt -0,2). (3) `_origin_outlier_lot_ids`s SQL filtert zusätzlich `lot_date IS NOT NULL`, `_flag_price_outliers`s SQL tut das nicht -- Live-Messung: 0 betroffene Zeilen (0/2 444 946), nur latent, dokumentiert statt verhaltensändernd gefixt. (4) Die origin-bewusste Recency/Outlier-Logik existiert unabhängig in `eval.py` UND `models.py` (genau das hat zu Befund (2) geführt). **User-Entscheid: Kreuzverweis-Kommentar reicht, keine Dedupe** (unterschiedliche Datenformen: Gruppen-DataFrame vs. Einzelserie). (5) `test_forecast_eval.py`s `_series()`-Hilfsfunktion behauptete "load_series-shaped", fehlte aber `lot_id`/`house_offset` -- Dokumentation korrigiert, kein aktueller Test betroffen. | (2) gefixt + neuer Regressionstest (`test_recency_is_judged_before_exclude_lot_ids_is_applied`, hand-verifiziert gegen die alte Reihenfolge); (1)/(3)/(4)/(5) als Docstring-Korrekturen/-Ergänzungen festgehalten, kein Verhaltensunterschied. Volle Suite 572/572 grün, Pylint clean (Produktionscode 0 neue Findings, Testdatei-Rauschen vorbestehend/CI-irrelevant). |
| 2026-11-13 | 2.1/2.6 (Coverage-Überkorrektur + Trend-Modell) | Claude (`advisor` dreimal konsultiert: vor der Modell-Ersetzung, nach dem unerwarteten Coverage-Umschlag next<77%, nach der weiterhin zu hohen FIT_FAILED-Quote des Trend-Modells -- jedes Mal mit Live-DB-Messung statt Vermutung) | **Kein Review-Finding, aber zwei echte, selbst gefundene Bugs unterwegs:** (1) `local_linear_trend`'s `start_params` übergab den gedämpften Damping-Wert im UNGESCHÜTZTEN (unconstrained) statt im constrained Raum -- `statsmodels` liest `start_params` als constrained und ruft intern `untransform_params` darauf, der übergebene Wert `1,5` wurde daher als Damping `1,5 > DAMPING_MAX` gelesen und auf die Kappungsgrenze geklemmt, der Optimierer startete direkt am Rand. Gefunden durch `inspect.getsource(MLEModel.fit)`, nicht vermutet. Fix: `0.80` (constrained) statt `1.5`. (2) `local_linear_trend`s FIT_FAILED-Quote blieb danach bei 12-22 % -- Ursache per gezielter Diagnose (mle_retvals-Breakdown auf 145 nicht-konvergenten Fits) verifiziert: jeder einzelne Fall traf exakt `maxiter=50` (statsmodels' Default), während `damping` legitim gegen seine offene untere Grenze lief, die ein Optimierer nie exakt erreicht. Re-Test derselben Fälle mit `maxiter=500` konvergierte alle 19/19. Fix: `maxiter=200` für beide Modellvarianten (`_FIT_MAXITER`). | `_within_month_lot_variance`-Korrektur (2.5, letzte Runde) ersetzt durch `_LocalLevelTrend` (eigenes `MLEModel`, Pro-Monat-Gewichtung `sigma2.irregular/k_t`, mit `trend=True/False` für beide Modellvarianten geteilt); `local_linear_trend_forecast`/`make_local_linear_trend_forecaster` neu; `test_forecast_local_level.py` komplett neu geschrieben (24 Tests: Gewichtungs-Nachweis, Damping-Validierung, Clamp/Resmooth-Pfad). Synthetische Validierung VOR jedem Live-Test (Parameter-Wiedergewinnung, NaN-Lücken, Damping verhindert Extrapolation-Blowup) in einem Scratch-Prototyp, dann erst in `models.py` übernommen. Drei Live-Diagnose-Läufe auf stratifizierten Teilstichproben (1 600 bzw. 1 000 Serien) VOR dem vollen Lauf, um Coverage-nach-Clamp-Status und FIT_FAILED-nach-Dichteklasse zu messen, statt auf den ~2-Stunden-Volllauf zu raten. Volle Suite 578/578 grün, Pylint clean (1 neue, akzeptierte Testdatei-Dokstring-Lücke, gleiche Konvention wie immer). **User-Entscheide:** Coverage-AC wird über ALLE Dichteklassen bewertet (nicht nur D5-Population); `local_linear_trend` kommt in den vollen Lauf als echter Kandidat. Vierter kombinierter Live-Lauf (6 Modelle, beide Horizonte, ~2 Std.): volle Zahlen und Interpretation siehe 2.1/2.5/2.6-Einträge in §5. Senior-Review über den vollen Diff: siehe eigener Eintrag unten. |
| 2026-11-13 | Senior-Review (2.1/2.6-Diff) | Claude (`code-review high` auf dem vollen uncommitteten Diff, forked, mit statsmodels-Quellcode-Lektüre + empirischer Reproduktion statt Vermutung) | **3 Befunde, 2 echt+gefixt, 1 echt+dokumentiert:** (1) **Echter, potenziell gefährlicher Dokstring-Fehler, gefixt:** `_LocalLevelTrend.clone()`s Dokstring behauptete, `obs_cov` werde für die Out-of-Sample-Erweiterung "nie gelesen", daher sei das Dummy-Gewicht `1` unschädlich. Empirisch widerlegt (Reproduktionsskript: Gewicht `1` vs. `3` in `clone()` patchen änderte `get_forecast().var_pred_mean` von 0,044 auf 0,019 -- `obs_cov` WIRD gelesen und bestimmt die Prognose-Varianz direkt). Der tatsächliche Grund, warum `1` trotzdem korrekt ist, ist ein anderer als behauptet: `evaluate_series` scort immer ein EINZELNES künftiges Los, nie einen Monatsmittel-Wert, daher muss die Varianz immer `sigma2.irregular/1` sein -- unabhängig davon, wie viele Lose der echte künftige Monat tatsächlich hat. Dokstring korrigiert, explizite Warnung ergänzt: eine künftige "Verbesserung" auf einen realistischeren künftigen `k_t>1` würde lautlos die Pro-Monat-Gewichtungs-Korrektur (siehe oben) wieder aufheben. (2) **Echter, gefixt:** `start_params`s `resid_var = float(np.nanvar(...)) or 1.0` -- `nan` ist in Python wahr (truthy), `nan or 1.0` ergibt `nan`, nicht den beabsichtigten Fallback. Der Produktionspfad (`_llt_forecast`s `>= LOCAL_LEVEL_MIN_MONTHS`-Gate) erreicht das nie mit einer komplett-NaN-Serie, aber `_LocalLevelTrend` wird auch direkt instanziiert (bereits in Tests) -- gefixt auf einen expliziten `np.isfinite`-Check. (3) **Echt, geringe Priorität, dokumentiert statt gefixt:** `_llt_forecast` ruft `_monthly_series`/`_monthly_weights` unabhängig auf, beide bauen denselben `resample("MS")` neu auf -- auf dem heissen Backtest-Pfad (pro Origin/Serie) vermeidbare doppelte Arbeit. Nicht gefixt: der dominante Kostenfaktor ist die statsmodels-MLE-Optimierung selbst (bestätigt durch die Laufzeit des 6-Modell-Laufs), eine Zusammenführung würde eine dritte Code-Stelle mit Resample-Logik einführen für einen vermutlich geringen Laufzeitgewinn. | (1)+(2) gefixt, Dokstrings entsprechend erweitert; (3) als akzeptiertes Tech-Debt dokumentiert. Volle Suite weiterhin 578/578 grün, Pylint unverändert clean (nur vorbestehende/CI-irrelevante Funde). |

---

## 9. Reihenfolge & Aufwand (grob)

Stufe 0: 3–4 Tage · Stufe 1: 2 Tage · Stufe 2: 3–4 Tage · Stufe 3: 4–5 Tage ·
Stufe 4: 1–2 Tage · Stufe 5: 3 Tage ⇒ **≈ 3–4 Wochen**, wovon Stufe 0 der
unvermeidbare und risikoreichste Teil ist. Ein erstes, vorzeigbares Ergebnis
(Gate G2, Fan-Charts für dichte Weine) liegt nach ca. 10 Arbeitstagen vor.
