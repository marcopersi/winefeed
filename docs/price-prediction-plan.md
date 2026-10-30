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
    brauchen den Fallback oder `INSUFFICIENT_DATA`.
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
- **Status: erledigt 2026-10-29** (`_normalize_lot_date` in `build_db.py`, vor `_fill_lot_date`). Verifiziert auf Kopie der Master-DB: 147 Zeilen konvertiert (alle steinfels), 0 Nicht-ISO übrig; `unittest discover -s data/tests` 115 Tests grün. Noch nicht in die Master-DB gebaut (nächster regulärer Build).
- **Neuer Befund 0.1b:** 680 Lose (winebarrel) haben `lot_date = 1970-01-01` (Epoch-Artefakt). Nicht stillschweigend ändern; Entscheid im Review: auf NULL setzen und aus `auction_date` füllen, oder aus `forecast_input` ausschliessen (`lot_date >= '1990-01-01'`). Bis dahin gilt der Ausschluss.

**0.2 Historische FX-Tabelle** (M)
- Neue Tabelle `fx_rates(date, currency, per_eur)`; Quelle: **EODHD** (EOD-Forex, Paare `<CCY>EUR.FOREX`; Tagesschlusskurse, Monatsmittel werden abgeleitet). Abruf-Skript `data/fetch_fx.py` liest den Key aus `EODHD_API_TOKEN`, cached Rohantworten im Archiv (Samsung), ist idempotent; Test mit gemockter HTTP-Antwort, kein Netz in CI. Abdeckung der Historie je Währung vorab prüfen (Start der Zeitreihe; Pre-Euro-Währungen). Für Zeiträume vor 1999: Fallback auf ein dokumentiertes Verfahren oder Ausschluss (`fx_missing`).
- Quelle **im Dokument festhalten** (URL, Abrufdatum, Lizenz). Das Skript ist idempotent und lädt keine Daten ohne explizite Aktion.
- AC: für alle (currency, Monat) der Lose existiert ein Kurs, ausser Währungen mit Flag; Bericht der Lücken.
- Test: Stichproben-Kurse gegen publizierte Werte (3 Datenpunkte als Fixture).

**0.3 `_annotate_fx` erweitern** (M)
- `fx_rate` (Einheiten je 1 EUR) und `fx_target_currency='EUR'` für *alle* Währungen via Lotdatum-Monat; Zeilen ohne Kurs: `fx_rate` NULL + `fx_status='MISSING'`.
- AC: `fx_rate`-Abdeckung ≥ 99 % der Zeilen mit Datum; NLG-Bestand unverändert (Regression: Hash der 4 854 NLG-Zeilen vor/nach identisch).

**0.4 Flaschengrösse klären** (M)
- Untersuchung: Welche Häuser liefern `bottle_size_dl`? Wo steht Info in `description`/`raw_wine` („Magnum", „1.5L", „75cl", „Jeroboam")? Einheit `1.0` (21 k Zeilen) prüfen: vermutlich Liter statt dl.
- Output: Entscheidungstabelle + Parser-Erweiterung in `data/wine_resolution/bottle.py` (existiert, ist aktuell modifiziert → vorher `git diff` lesen, nicht überschreiben).
- Default-Regel: `NULL` → 7,5 dl **nur** mit Flag `size_assumed=1`; Magnum etc. werden als eigene Serie geführt oder per Äquivalent-Faktor normiert (Entscheidung D10, siehe §6 offene Punkte).
- AC: Verteilung `bottle_size_dl` nach Fix dokumentiert; `NULL`-Anteil < 10 % oder je Haus begründet; Stichprobe 100 Lose manuell geprüft, Fehlerquote < 3 %.

**0.5 `price_per_bottle` befüllen** (M)
- Formel: `realised_price / quantity / (bottle_size_dl/7.5)`, Basis gemäss D1; bei fehlendem `realised_price`: aus `hammer_price + buyer_premium` ableiten (`price_source=DERIVED`).
- `quantity IS NULL` → 1 mit Flag `qty_assumed`; `quantity > 12` → Flag `QTY_SUSPECT` (wahrscheinlich Mischlos / Kartons).
- Neue Spalten: `price_per_bottle_eur`, `ppb_flags`.
- AC: ≥ 85 % der `single_wine_prices` haben `price_per_bottle_eur`; Verteilung je Haus (Median, P1, P99) im Report; keine Werte ≤ 0.
- Test: Tabelle von Los-Konstellationen → erwarteter Flaschenpreis.

**0.6 Outlier- und Dubletten-Bereinigung** (M)
- Dubletten: gleiche (wine_ref_id, Jahrgang, Datum, Preis ±1 %, Haus) → eine Zeile; idealwine („cote") als eigene Preisart `price_kind='COTE'` ausschliessen oder getrennt führen (Entscheid in Review).
- Ausreisser: robuste z-Score (MAD) im Log-Preis je Gruppe, |z|>5 → `ppb_flags += 'OUTLIER'` (**nicht löschen**, nur markieren; Modell entscheidet).
- AC: Anzahl markierter/entfernter Zeilen pro Haus im Report; Stichprobe 50 markierte Zeilen manuell geprüft.

**0.7 View `forecast_input`** (S)
- `select wine_ref_id, vintage, size_class, lot_date, auction_id, provider_id, y=ln(price_per_bottle_eur), …` mit `sold IS NOT 0`, ohne `OUTLIER`/`QTY_SUSPECT`/`fx_missing`.
- AC: Zeilenbilanz Rohdaten → Input mit Verlust je Ursache (Tabelle), Summen stimmen.

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

**Entschieden am 2026-10-29:**
D10 Grossformate = **eigene Reihen** (Schlüssel `wine_ref_id · vintage · size_class`, kein Äquivalent-Faktor) ·
D11 idealwine-`cote` / Schätzwerte = **nicht in die Serien** (`price_kind='COTE'` ausgeschlossen) ·
D13 FX-Quelle = **EODHD** (vorhandenes Abo; API-Key nur via Umgebungsvariable, nie im Repo; Quelle/Abrufdatum in der Doku festhalten) ·
D14 `sold IS NULL` = **nicht werten** (Filter in `forecast_input`: `sold = 1`; Folge: ~62 % der Zeilen entfallen → Dichte in §2.10 neu messen, siehe 0.7).
Offen bleiben D12 (Anzeigewährung) und D15.

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
| – | – | – | – | – |

---

## 9. Reihenfolge & Aufwand (grob)

Stufe 0: 3–4 Tage · Stufe 1: 2 Tage · Stufe 2: 3–4 Tage · Stufe 3: 4–5 Tage ·
Stufe 4: 1–2 Tage · Stufe 5: 3 Tage ⇒ **≈ 3–4 Wochen**, wovon Stufe 0 der
unvermeidbare und risikoreichste Teil ist. Ein erstes, vorzeigbares Ergebnis
(Gate G2, Fan-Charts für dichte Weine) liegt nach ca. 10 Arbeitstagen vor.
