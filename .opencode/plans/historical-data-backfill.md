# Bauplan: Historische Daten-Lücken schliessen (Backfill + Fetch-Härtung)

> **Status:** In Arbeit. Entstanden aus einem vollständigen Audit aller ~36
> Provider (2026-11-24): für jeden `load_*` in `data/build_db.py` wurde
> geprüft, ob ALLE Dateien im Samsung-Archiv
> (`/Volumes/samsung/winefeed-data/WeinAuktionspreise/`) tatsächlich vom
> jeweiligen Loader erfasst werden. Auslöser war ein Race-Condition-Bug beim
> Koppe-Rebuild (DB-Build lief, während der Archiv-Sync noch schrieb) — das
> hat eine systematische Prüfung aller Häuser nötig gemacht statt nur
> Stichproben.
>
> **🔴 NEUER, VORRANGIGER FUND (2026-11-24, beim Verifizieren des Koppe-Fixes
> entdeckt): Doppelzählung, nicht nur fehlende Daten.** 57 Auktionen über
> 5 Häuser (hdh 83.841 Lots über 42 Auktionen, sylvies 11.994, winefields
> 4.851, finarte 4.039, koppe 902 — total ~105.627 doppelt gezählte
> Lot-Zeilen) werden aus ZWEI verschiedenen Archiv-Dateipfaden geladen, die
> dieselbe echte Auktion enthalten (bestätigt für koppe/10: identisches
> erstes Lot "Chateau Haut-Brion 1998, 6.000 EUR" in
> `Koppe/10.json` UND `Koppe/2026/08_August/auction-10.json`). Vermutete
> Ursache: ältere, datierte Archiv-Struktur (vor dem Manifest-System) +
> aktueller Fetcher kennt diese alten IDs nicht im Manifest und schreibt sie
> erneut flach ins Archiv — der Loader lädt dann beide. **Das betrifft die
> BEREITS AUSGELIEFERTE Produktions-DB, nicht nur offene Backlog-Arbeit —
> wird VOR dem Rest von Phase 1/2 behoben.** Siehe Phase 0 unten.

> **Arbeitsweise (zwingend, user-vorgegeben):** Strikt sequenziell, ein Punkt
> nach dem anderen. Ein Punkt gilt erst als erledigt, wenn (a) die Daten
> wirklich verarbeitet/gefixt sind, (b) ein Sanity-Check das mit echten
> Zahlen belegt, (c) Senior-Review vor Commit durchlaufen ist
> ([[feedback_senior_review_before_commit]]). Erst dann der nächste Punkt.
> Reihenfolge innerhalb einer Phase ist ein Vorschlag (aufsteigende
> Komplexität, um das Sanity-Check-Muster günstig zu etablieren), kein Dogma.

---

## Phase 0 — 🔴 Doppelzählung durch Mehrfach-Dateipfade pro Auktion fixen — ✅ erledigt

- [x] Vollen Umfang bestätigt: nicht nur die ersten 57 "exakt gleiche
  Lot-Zahl"-Fälle — eine strukturelle Prüfung (flacher Pfad `Haus/<id>.json`
  UND datierter Pfad `Haus/<jahr>/<monat>/<id>.json` für dieselbe
  auction_id gleichzeitig vorhanden) fand **119 Auktionen über 6 Häuser**
  (hdh 94, finarte 9, winefields 6, pandolfini **5 — auch der bestehende
  LIVE-Loader, nicht nur meine neue Legacy-Variante!**, besch-cannes 4,
  koppe 1) plus **sylvies** als eigenes Muster (6 Monate, .zip UND .json
  für dieselben Monate geladen — kein Pfad-, sondern ein Format-Duplikat).
  steinfels (146) und weinboerse (9) wurden geprüft und als FALSCH-POSITIV
  verifiziert — das sind reine Mehrseiten-Paginierungen derselben Auktion
  (`Resultfile1/2/3/4.json`), kein Duplikat.
- [x] Fix in `data/build_db.py`: neue `_dedupe_auction_files(files, id_fn)` —
  liest jede Kandidaten-Datei einmal vorab, gruppiert nach der Auction-ID,
  die der jeweilige Loader daraus bauen würde, behält pro ID nur die Datei
  mit den MEISTEN Lots (jeder Stichprobe von Hand bestätigte: die
  vollständigere Fassung ist nie eine disjunkte andere Auktion, immer
  dieselbe, nur evtl. unterschiedlich oft nachgefetcht). Angewendet auf
  `load_hdh`, `load_winefields`, `load_beschcannes`, `load_finarte`,
  `load_koppe`, `load_pandolfini` (Live-Loader). Für `load_sylvies_fetched`
  stattdessen gezielter Fix: überspringt jetzt Monate, die
  `load_sylvies_html` (die "volle Fidelity"-Quelle laut eigenem Docstring)
  bereits geladen hat, über die schon vorhandene
  `_sylvies_html_covered_months`-Prüfung.
- [x] Sanity-Check: strukturelle Duplikat-Abfrage nach dem Fix erneut
  laufen lassen (in-memory, gegen das echte Archiv) — **0 verbleibende
  Fälle**. Vorher/Nachher pro Haus (in-memory-Testlauf):
  hdh 569.785→342.114 (**-227.671**), sylvies-fetched 279.472→267.478
  (**-11.994**), winefields 93.838→88.987 (**-4.851**),
  besch-cannes 60.345→60.249 (**-96**), finarte 20.631→16.592 (**-4.039**),
  koppe 16.751→15.849 (**-902**), pandolfini (Live) 2.379→2.229 (**-150**).
  **Total: ~249.703 doppelt gezählte Lot-Zeilen entfernt** — deutlich mehr
  als die erste grobe Schätzung (105.627), weil die erste Abfrage nur
  exakt gleiche Lot-Zahlen fand, nicht alle flach/datiert-Paare mit leicht
  abweichender Zahl (z.B. 920 vs. 1018 bei hdh/1109 — derselbe Fall,
  nur zu unterschiedlichen Zeitpunkten nachgefetcht).
- [ ] **Noch ausstehend:** finaler Rebuild gegen die echte Samsung-DB mit
  allen Phase-0- UND Phase-1-Fixes zusammen (nicht einzeln, um nicht
  mehrfach einen 15-20-min-Vollbuild zu fahren) — läuft nach Abschluss von
  Pandolfini (Senior-Review) und den übrigen Phase-1-Punkten.

---

## Phase 1 — 6 Auktionshäuser: historische Rohdaten nachverarbeiten

Ziel pro Haus: ein Parser, der die bisher unverarbeiteten Rohdateien liest
und als zusätzliche Auktionen/Lots in die Master-DB einspeist (zusätzlich zum
bestehenden Loader, keine Ersetzung). Jeder Parser landet als eigene
`load_<haus>_legacy`-Funktion (oder äquivalent) in `data/build_db.py`, in
`HOUSES` registriert.

**Sanity-Check-Schema je Haus (Mindestanforderung):**
1. Dateianzahl vorher/nachher: wie viele Rohdateien wurden gelesen vs. wie
   viele existieren tatsächlich im Archiv (100% Abdeckung oder begründete
   Differenz, z.B. Index-/Leerdateien).
2. Stichprobe: mindestens 2 Dateien manuell gegen die Live-Lot-Liste in der
   DB geprüft (Weinname, Preis, Datum stimmen).
3. `_validate_gates` läuft ohne neue Fehler durch (Duplicate-Lot-Warnungen,
   Foreign-Key-Check etc.).
4. Vorher/Nachher-Zeilenbilanz dokumentiert (Auktionen+/Lots+ pro Haus).

### 1. Pandolfini — ✅ vollständig erledigt (alle 3 wiederherstellbaren Auktionen)
- [x] Rohdateien gesichtet: **3** wiederherstellbare historische Auktionen
  (11.12.2015, 15.04.2016, 20.10.2016). `2018/Catalogo_vini_ottobre_bassa.pdf`
  (29./30.10.2018) ist NUR ein Vorverkaufskatalog (188 Seiten, ausschliesslich
  "Euro X/Y"-Schätzpreise, kein "Price realized" je gefunden) — kein
  Ergebnis je archiviert, nicht wiederherstellbar, kein Fund.
- [x] Erste Runde fand 2 Auktionen (HTML-basiert) + stellte die dritte
  (Ottobre2016) zurück, weil ein erster Spalten-PDF-Prototyp nur 194/255
  Lots schaffte. **Senior-Review (automatisch vor jedem Commit) deckte dabei
  einen weiteren, schwereren Fund auf**, bevor committed wurde: die
  2015-12-11-Auktion hatte eigentlich 256 verkaufte Lots
  (`sold-unsold-list-2015.pdf`), die erste Fassung hatte davon nur 91 aus
  den HTML-Seiten geladen — 177 echte, preisbelegte Lots fehlten. Das
  bestätigt nochmal, warum die Senior-Review-Pflicht vor jedem Commit
  wichtig ist (siehe [[feedback_senior_review_before_commit]]).
- [x] **Generischer, spalten-bewusster PDF-Katalog-Parser gebaut**
  (`_pandolfini_catalog_lots`, `_pdf_lot_price_table` in `data/build_db.py`)
  statt die Lücke nur zu dokumentieren — Nutzer-Entscheidung im Chat:
  "Generellen Parser jetzt bauen". **Schlüssel-Fix:** Los-Nummern stehen in
  ~22pt-Schrift, aller andere Text in ~8.5pt — Erkennung über Schriftgrösse
  statt über eine monotone Ziffernfolge-Heuristik behob zwei false-positives
  auf einen Schlag (eine einzeln umgebrochene Mengenangabe wie "6 bt" wurde
  fälschlich als neue Losnummer erkannt und hat den VORHERIGEN Lot-Block
  abgeschnitten; Losnummern mit Sternchen-Suffix wie "180*" wurden von der
  reinen Ziffern-Regex gar nicht erkannt). Ergebnis: **255/255** (Ottobre2016)
  bzw. **280/280** (2015-12-11, inkl. der 5 Showcase-Lots, die vorher nur aus
  dem HTML bekannt waren) Katalog-Einträge, keine leeren Blöcke mehr.
- [x] Encoding-Bug (2016-04-15-Pfad, HTML): Seiten deklarieren `iso-8859-1`,
  tatsächlich aber `cp1252` (€-Zeichen = Byte 0x80) — behoben.
- [x] Einzelwert-Schätzpreis-Bug (kein "/", z.B. nur "€ 1.500") gefixt:
  wurde vorher silently auf `None` gesetzt statt als low=high gespeichert.
- [x] Sanity-Check je Auktion (alle in-memory gegen das echte Archiv
  verifiziert): 2015-12-11 → 280 Lots total, 256 mit Preis, 280 mit
  Weinname, 0 Duplikate; 2016-10-20 → 255 Lots, 207 mit Preis, 255 mit
  Weinname, 0 Duplikate; 2016-04-15 (unverändert HTML-basiert, Preis-Zahl
  261 Verkauft gegen `Resultat_2016.pdf`s eigene 261 Verkaufszeilen exakt
  gegengerechnet) → 276 Lots, 261 mit Preis. `PRAGMA integrity_check` ok.
  Stichproben (Lot 1 "Salon", 1.562€; Lot 100 "Château Lafite Rothschild
  2000", 2.280€; Ottobre2016 Lot 1, 2.818€) direkt gegen Rohtext verifiziert.
- [x] **Noch nicht in die echte Master-DB eingespielt** — läuft im finalen
  Rebuild am Ende von Phase 1 (siehe unten), nicht einzeln, um nicht
  mehrfach einen 15-20-minütigen Vollbuild zu fahren.
- [ ] **Bekannter, NICHT neu eingeführter Nebenbefund (Senior-Review):**
  Mehrflaschen-/Magnum-Lots (z.B. "1 bt DMg") werden weder hier noch im
  bestehenden `load_pandolfini` (Live-JSON-Loader) korrekt in
  `bottle_size_dl`/`quantity` aufgelöst — betrifft 162/276 bestehende UND
  einen Teil der 811 neuen Zeilen. Das ist eine vorbestehende, auftrags-
  übergreifende Datenqualitätsfrage (nicht Teil von "fehlende Auktionen
  nachladen"), separat vormerken, nicht hier blockieren.

### 2. Sothebys — ~10 Auktionen, 2011–2015 — **grösser/härter als erster Audit dachte**
- [ ] Rohdateien klassifiziert (2026-11-24, voller Scan aller 32 PDFs via
  pdftotext + Grep): zwei Dateitypen pro Auktion (plus ein paar
  Nicht-Treffer wie der 2015 Annual Report und eine Navigationsseite,
  beide ignoriert):
  - `<SaleNr>-Results.pdf` (oder `Results<SaleNr>.pdf`, `<SaleNr>_Results.pdf`):
    kurz (2-8 Seiten), **reine Lot/Preis-Tabelle ohne Weinnamen**
    (`LOT GBP  LOT GBP  LOT GBP ...` mehrspaltig) — genau wie Pandolfinis
    Ottobre2016-Preistabelle, aber SAUBER (einfaches Tabellenformat, kein
    Katalog-Rauschen).
  - `<SaleNr>-SALE.pdf` (bzw. `-t.pdf`, `_wine.pdf`): lang (64-236 Seiten),
    **voller Katalog mit Weinname + Beschreibung + Schätzpreis, aber OHNE
    Resultate** — 2-spaltiges Layout, Losnummer steht als kleine Zahl vor
    der Mengenangabe ("1   9 bts (cn)"), Schätzung als "per lot: £X-Y"
    (zusätzlich parallel in USD/EUR, nur GBP relevant).
  - Gleiche Problemklasse wie Pandolfini-Ottobre2016: Preis und Weinname
    stehen in ZWEI verschiedenen Dokumenten, müssen über die Losnummer
    gejoint werden — aber hier für **~10 Auktionen statt 1**, mit
    mindestens 2 erkennbaren Katalog-Vorlagen (Londoner `L*`-Sales 2-spaltig
    wie oben gezeigt; `HK*`/`N*`-Sales noch nicht einzeln geprüft, evtl.
    weitere Layout-Varianten).
  - Nicht relevant (geprüft, verworfen): `Sotheby's Wine 2015 Annual Report.pdf`,
    `Sotheby's | Auctions...pdf` (Navigationsseite), `04042015.pdf`/`14112015.pdf`
    (noch unklar, niedrige Priorität, kein Results-Pendant gefunden)
- [ ] **Entscheidung nötig, siehe Chat:** lohnt sich ein genereller,
  spalten-bewusster PDF-Katalog-Parser (pdfplumber-Wortkoordinaten, wie im
  Pandolfini-Prototyp begonnen) jetzt zu bauen — er würde SOWOHL
  Sothebys (alle ~10 Auktionen) ALS AUCH das zurückgestellte
  Pandolfini-Ottobre2016 lösen? Oder Sothebys vorerst zurückstellen,
  weil der Aufwand grösser ist als ursprünglich eingeschätzt?
- [ ] Parser schreiben, Sanity-Check, committen (sobald Entscheidung steht)

### 3. MunichWineCompany — ~11 Auktionen, 2016–2023
- [ ] Rohdateien: 673 HTML (`live-wineauction-pN.html`, `Resultatfile*.html`), in Monatsordnern (April2023, Juni2016, Nov2016-2019, Sep2015/2016/2019-2021)
- [ ] Kein wiederverwendbarer Konverter (`pythonParser.py` ist unfertiger Prototyp, nicht nutzbar) — Parser von Grund auf
- [ ] Kein Überlapp mit bestehender DB (DB beginnt ~2024/2025) — reiner Zugewinn
- [ ] Parser schreiben, Sanity-Check, committen

### 4. Koppe — mehrjährige Lücke (2015–2020) + 3 Auktionen 2026 (Wayback)
- [ ] Teil A: Rohdateien 2015–2020 (`Resultatfile*.html`, `Auktionskatalog*.pdf`, `Ergebnis*.pdf`) im Archiv unter Jahresordnern — Umfang noch zu quantifizieren (Dateianzahl zählen, Stichprobe öffnen)
- [ ] Teil B: Auktionen intern 518/519/520 (= ids 5/6/7, Jan–März 2026) — von der Live-Seite nach Retention-Fenster entfernt, nur via Wayback-Machine-CDX-API rekonstruierbar (altes URL-Schema `?site=auktion&section=cat&cat={id}&p={n}` / `?site=auktiondetail&...`, Snapshots vorhanden zurück bis 2019, speziell für `cat=518` 46 Snapshot-Zeilen bestätigt)
- [ ] Beide Teile: Parser schreiben (Teil A: lokales HTML/PDF; Teil B: Wayback-Fetch + Parsing), Sanity-Check, committen

### 5. Steinfels — ~54 Auktionen, #325–#378, ca. 2004–2015
- [ ] Rohdateien: `Katalog_*.pdf`, `Lotliste_*.xls(x)`, `Resultate_*.pdf`
- [ ] Bestätigt echt: `Katalog_384_252.pdf` (Lot 1–861+)
- [ ] Technisches Hindernis: manche `Lotliste_*.xls` sind altes Binär-`.xls`, nicht `.xlsx` — openpyxl liest das nicht, braucht `xlrd` o.ä. oder Konvertierung
- [ ] Parser schreiben, Sanity-Check, committen

### 6. Weinboerse — ~20 Auktionen, #78–#101, ca. 2010–2019
- [ ] Rohdateien: gleiches Katalog/Resultate/Gebote-PDF/XLS-Muster wie Steinfels — noch nicht einzeln geöffnet/bestätigt, als erster Schritt hier nachholen
- [ ] Da AUEX-Plattform wie Steinfels (user-bestätigt): ggf. Parser-Code von Steinfels (Punkt 5) wiederverwendbar
- [ ] Parser schreiben, Sanity-Check, committen

### Abschluss Phase 1 (nach Punkt 6)
- [ ] EIN finaler, vollständiger `build_db.py`-Lauf gegen die Samsung-Disk
  (nur wenn Archiv nachweislich ruhig — kein laufender Sync/Build, s.
  [[feedback_zero_data_loss_systematic_verification]])
- [ ] Pro neu hinzugefügtem Haus: Auktionszahl/Lot-Zahl/% mit Preis in der
  echten DB verifizieren (wie beim Koppe/MunichWineCompany-Check am
  2026-11-24), nicht nur in der isolierten In-Memory-Prüfung
- [ ] `_validate_gates` lief ohne neue Fehler
- [ ] Commit mit Vorher/Nachher-Zeilenbilanz aller 6 Häuser zusammen

---

## Phase 2 — 5 Fetch-Lücken schliessen (nicht Loader-Bug, sondern "nie/nicht mehr gefetcht")

Ziel pro Punkt: Root Cause fixen, fehlende Daten nachholen, UND einen
Guardrail einbauen, der ein Wiederauftreten künftig automatisch sichtbar
macht (nicht nur den aktuellen Stand reparieren).

**Sanity-Check-Schema je Punkt:**
1. Root Cause bestätigt (nicht nur vermutet).
2. Fix angewendet, fehlende Daten nachgeholt (wo möglich) — mit Vorher/Nachher-Zahlen.
3. Guardrail/Regression-Schutz eingebaut (z.B. CI-Check, Assertion, Monitoring-Hinweis) und einmal bewusst gegen den alten Zustand getestet, dass er wirklich anschlägt.
4. Committen.

### 1. idealwine — CI-Fetch seit ~3 Monaten tot
- [ ] Root Cause: `algolia.idealwine.com` DNS tot (bekannt seit Run 45364027030, 2026-11-24)
- [ ] Fix: aktuellen API-Host von idealwine ermitteln (ggf. hat sich die Such-Infrastruktur geändert), `run_idealwine_delta.py` anpassen
- [ ] Nachholen: fehlende ~3 Monate Cote-Zuschläge fetchen
- [ ] Guardrail: CI-Step soll bei DNS-Fehlern lauter failen/alerten statt nur `continue-on-error` zu konsumieren (aktuell schluckt das den Fehler für immer, ohne dass es auffällt)

### 2. weinauktionator — IDs 23, 27 fehlen komplett
- [ ] Root Cause prüfen (nie gefetcht? gelöscht? Nummerierungslücke beim Haus selbst?)
- [ ] Nachholen falls abrufbar
- [ ] Guardrail: Lücken-Check (erwartete fortlaufende IDs vs. tatsächlich vorhandene) als Teil des Ingest-Laufs

### 3. franzwermuth — Collections 2, 4 fehlen komplett (keine Datei, kein Katalog)
- [ ] Root Cause prüfen (Fetcher-Historie, ggf. nie existiert vs. nie gefetcht)
- [ ] Nachholen falls möglich
- [ ] Guardrail: wie weinauktionator — Lücken-Check auf erwartete Collection-Nummern

### 4. besch-cannes — `auctions_directory.json` listet mehr IDs als je gefetcht
- [ ] Root Cause: Differenz zwischen Index und tatsächlich geladenen `auction-*.json` quantifizieren (welche IDs genau fehlen)
- [ ] Nachholen der fehlenden IDs
- [ ] Guardrail: Ingest-Lauf vergleicht `auctions_directory.json` gegen vorhandene Dateien und meldet Differenz

### 5. Zacky — 248 HTML-Dateien ungeklärt
- [ ] Erst klären, ob es überhaupt eine echte Lücke ist (Stichprobe sah nach Such-Listing-Seiten aus, nicht nach Losdetails) — vollständige Sichtung aller 248 Dateien, nicht nur 1
- [ ] Falls echte Lot-Daten drin: nachholen wie die anderen Punkte
- [ ] Falls keine Lot-Daten (nur Navigationsseiten): als "kein Fund" dokumentieren und abschliessen
- [ ] Guardrail nur falls echter Fund

---

## Nicht Teil dieses Plans (bereits erledigt oder separat)

- Sync-Race-Condition-Fix (Build nur bei nachweislich ruhigem Archiv starten) — bereits als Lektion in [[feedback_zero_data_loss_systematic_verification]] festgehalten, nicht nochmal hier.
- Ampersand-Fetcher (neues Haus) — bewusst zurückgestellt, bis dieser Plan (Phase 1 + 2) vollständig abgeschlossen ist.
