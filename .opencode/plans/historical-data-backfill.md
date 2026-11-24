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

### 2. Sothebys — ⏸ zurückgestellt nach Versuch (deutlich aufwändiger als erwartet, siehe unten)
- [x] Nutzer-Entscheidung im Chat bestätigt: genereller spalten-bewusster
  Parser sollte gebaut werden (gilt für Sothebys UND Pandolfini-Ottobre2016
  — Letzteres ist bereits fertig, siehe Punkt 1).
- [x] Katalog-Layout analysiert: 2-spaltig (nicht 3 wie Pandolfini), Los-
  Nummer sitzt MITTEN im Block (nach Weinname/Beschreibung, vor den 3
  "per lot: <WÄHRUNG><Spanne>"-Zeilen GBP/USD/EUR) statt am Blockanfang —
  brauchte eine eigene Segmentierungslogik (Pandolfinis "Marker startet
  Block" passt hier nicht).
- [x] Font-Unterscheidung gefunden (Los-Nummer in "...-Book", Fliesstext in
  "...-Light", gleiche Grösse 9.5pt — anders als Pandolfini, wo die Grösse
  selbst der Marker war).
- [ ] **Abgebrochen nach drei Iterationen, weil die Spaltenposition NICHT
  konstant ist**: Recto/Verso-Seiten (Druck-Bindung) verschieben die
  Spalten-x-Positionen zwischen z.B. x0≈35/301 und x0≈48/314 abwechselnd,
  UND die Font-Namen-Zuordnung über Zeichen-Position war zusätzlich
  fehleranfällig (Rundungs-Mismatch) — mit `extract_words(extra_attrs=...)`
  statt manueller Zeichen-Positions-Lookup-Tabelle gefixt, aber selbst
  danach nur **151 von 403 Lots** auf der ersten geprüften Auktion
  (L11710, 05.10.2011) zuverlässig erkannt — zu unvollständig für einen
  stillen Import, und mit noch unbekannter Ursache für die verbleibende
  Lücke.
- [ ] **Entscheidung: zurückgestellt, NICHT weiter Zeit investiert jetzt** —
  Begründung: 10 Auktionen mit mindestens 2 Katalog-Vorlagen (L-London,
  weitere HK/N-Varianten ungeprüft) bei bereits 3 gefundenen Encoding-/
  Positions-Problemen auf nur EINER Auktion ist ein deutlich größeres,
  unsicheres Aufwands-Fass als Pandolfini war. Steinfels/Weinboerse (vom
  Nutzer am Anfang der Session explizit als wichtig genannt, AUEX-Plattform)
  und MunichWineCompany/Koppe-Rest haben Priorität — Sothebys wird NACH
  diesen fortgesetzt, nicht verworfen. Alle Zwischenergebnisse/Skripte
  liegen im Scratchpad (`sothebys_catalog3.py`), nicht committed (noch
  nicht zuverlässig genug für Produktionscode).

<details>
<summary>Ursprünglicher Befund vor dem Parser-Versuch (unverändert als Kontext)</summary>

~10 Auktionen, 2011–2015 — **grösser/härter als erster Audit dachte**
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
- [ ] Parser-Versuch: siehe oben, abgebrochen bei 151/403 Lots, zurückgestellt.

</details>

### 3. MunichWineCompany — ✅ erledigt (8 von 8 wirklich erhaltenen Auktionen, 8.394 neue Lots)
- [x] Vollständige Dateityp-Prüfung über ALLE 27 Monatsordner (nicht nur die
  vom Erst-Audit vermuteten ~11): April2023 (64 Dateien), September2020
  (57), September2021 (61) sind **zu 100% tote Fehlerseiten** (exakt
  944 Bytes, identischer "veralteter Link"-Platzhaltertext) — keine
  echten Daten, nichts zu holen. Die numerischen Jahresordner (2007-2024)
  enthalten `.json` und sind bereits vom bestehenden Loader erfasst.
  März2016/September2015/Oktober2018/Maerz2021 sind einzelne PDF/XLS-
  Dateien (anderes Format) — nicht verfolgt, niedrigeres Volumen, bei
  Bedarf separat.
- [x] **8 wirklich echte historische Auktionen** gefunden und geladen.
  **Senior-Review fand 3 weitere echte Bugs, alle gefixt:** (1) Region/
  Mengenangabe waren an falscher Position gelesen (fixe `body[N]`-Indizes
  statt Muster-Suche) und kamen bei praktisch jedem Lot als `None` zurück
  — jetzt per Pattern-Suche robust gegen variable Zeilenzahl gefunden;
  (2) 3 der 8 Daten (Juni2016, September2019, November2019) waren bereits
  SPARSAMER im bestehenden JSON-Loader vorhanden (z.B. Juni2016: nur 160
  von 1.176 Lots, unter numerischen IDs `154`/`156`) — hätte doppelt
  gezählt; jetzt fragt der Loader vor dem Laden die schon vorhandenen
  `lot_no`s für dasselbe Datum ab und überspringt sie, statt die
  7x-vollständigere HTML-Fassung entweder zu duplizieren oder ganz zu
  verwerfen; (3) Herkunfts-Datei zeigte für JEDEN Lot auf die zuletzt
  verarbeitete Seite statt die tatsächliche — jetzt pro Lot korrekt
  mitgeführt. **Finale Zahl nach allen Fixes: 7.974 neue Lots** (nicht
  8.394 — die Differenz sind genau die beim bestehenden JSON-Loader schon
  vorhandenen, korrekt nicht doppelt geladenen Lots).
- [x] Format: Fliesstext-Listen-Seiten (kein Spalten-Layout wie bei
  Pandolfini/Sothebys — viel einfacher), Lot-Block endet immer am Link
  "» merken", Preis als "Zuschlag bei EUR X" (= hammer, nur bei verkauft)
  bzw. nur "EUR X - Y" (Schätzung) bei unverkauft.
- [x] **Zweite Senior-Review (Multi-Agent) fand 6 weitere echte Bugs, alle
  gefixt:** Pagination-Ziffern ("11","12",...,"19") konnten fälschlich als
  Losnummer erkannt werden (jetzt ausgeschlossen: echte Losnummer steht
  nie direkt vor einer weiteren nackten Zahl); Region-Regex erkannte eine
  nackte Jahreszahl in Klammern wie "(2015)" fälschlich als Region (jetzt
  Ziffer-Only ausgeschlossen); Dedup gegen den bestehenden JSON-Loader
  verglich lot_no ohne führende Nullen zu normalisieren; Titel-Suche brach
  beim ERSTEN title-Tag ab statt bei einem mit erkennbarem Datum (hätte
  den Datums-Dedup für genau die 3 überlappenden Monate lautlos
  deaktiviert); doppelte Preis-Parsing-Funktion entfernt (euro_int
  wiederverwendet statt eigene Kopie); Dedup zwischen den zwei
  Namenskonventionen (live-wineauction-pN.html vs. ResultatfileN.html)
  bevorzugt jetzt explizit die Kopie MIT Zuschlag statt blind die zuletzt
  verarbeitete Datei zu nehmen. Alle Fixes erneut gegen das echte Archiv
  verifiziert (gleiche 7.974 Lots, 0 Cross-Auktion-Duplikate, 0
  Jahreszahl-als-Region-Fälle).
- [x] **Fund: November2017 ist eine ECHTE, aber UNVOLLSTÄNDIGE Aufnahme**:
  alle 68 archivierten Seiten enthalten identisch dieselben ersten ~20
  Lots — ein Paginierungs-Bug im ursprünglichen Scrape-Lauf selbst (nicht
  mein Parsing), der Rest dieser Auktion wurde nie wirklich erfasst.
  Geladen mit den echten 20 Lots, nicht übersprungen, aber als bekannte
  Lücke dokumentiert — nicht weiter rekonstruierbar ohne die Originalseite.
- [x] Sanity-Check: rohe Lot-Nummern-Lücken pro Auktion geprüft — Juni2016
  (0 Lücken, 1-1176 lückenlos), September2016/November2018 (2-3 Lücken,
  plausibel = vom Haus zurückgezogene/nie vergebene Nummern wie bei
  Koppe/Pandolfini), November2016/Oktober2018 (~160-260 verstreute
  Einzel-Lücken, gleiche plausible Erklärung, KEIN systematisches Muster
  wie bei November2017). 0 doppelte `lot_no` über alle 8 Auktionen.
  `PRAGMA integrity_check` ok. Datum korrekt aus Titel-Text extrahiert
  (Bug gefixt: einstellige Tage/Monate wie "4.06.2016" wurden zunächst
  nicht erkannt).
- [ ] Noch nicht in die echte Master-DB eingespielt — läuft im finalen
  Rebuild am Ende von Phase 1.

### 4. Koppe — ⏸ Umfang viel grösser als geschätzt, noch nicht begonnen
- [x] Teil A neu vermessen (2026-11-24): nicht nur "2015-2020" — die Katalog/
  Ergebnis-PDF-Paare reichen durchgehend von **2015 bis 2024** (gezählt:
  40+ Paare, u.a. `Ergebnis.pdf`/`katalog.pdf` pro Monatsordner 2015-2019,
  dann durchnummeriert 414-454, 483-488 ab 2020). Format: Ergebnis-PDF ist
  eine einfache "Lotnr./Preis"-Tabelle (wiederverwendbar mit
  `_pdf_lot_price_table`, bereits gebaut für Pandolfini), ABER die
  Katalog-PDF hat dasselbe schwierige 2-spaltige "Marker-mitten-im-Block"-
  Layout wie Sothebys (Losnummer klein, vor der Mengenangabe, kein grosser
  Font wie bei Pandolfini) — mit identischem Aufwandsrisiko.
- [ ] Teil B (3 Auktionen 2026, Wayback): unverändert offen, Fund von
  gestern — `cat=518/519/520`, altes URL-Schema, Snapshots bis 2019
  zurück vorhanden, 46 Snapshot-Zeilen für `cat=518` bestätigt.
- [ ] **Entscheidung: zurückgestellt zusammen mit Sothebys** (Punkt 2) —
  gleiche Begründung: 2-spaltiges Marker-mitten-im-Block-Katalog-Layout,
  jetzt für ~40 Auktionen statt einer Handvoll. Nicht jetzt in diese
  Session gequetscht.

### 5. Steinfels — ⏸ Format uneinheitlich über die Jahre, noch nicht begonnen
- [x] Lotliste/Ergebnis-Paare für ALLE Jahre gesichtet (2009-2022, nicht nur
  "#325-378"): **sehr positiver Teilbefund** — ab 2014 liegt die Katalog-
  Seite als **strukturierte Tabelle** vor (`Lotliste_*.xls(x)`: LotNr,
  Produkt, Appellation, Jahrgang, Lot Menge, Schätzung — mit `xlrd` lesbar,
  kein PDF-Spalten-Problem!) UND die Ergebnis-Seite ist eine **saubere,
  nicht-interleaved Tabelle** (`Lot Nr. | Produkt | Menge | Jahrgang |
  Zuschlag`, pdftotext -layout reicht, kein Sothebys-artiges Problem).
  Für EINE Stichprobe (Auktion 384, Juni 2017) bestätigt: 2065 Lots,
  klar lesbar, Preis direkt in der letzten Spalte.
- [x] **Aber**: 2009-2013 haben NUR Ergebnis-PDFs, KEINE Lotliste — unklar
  ob die Ergebnis-PDF dort überhaupt Weinnamen enthält oder nur Lot+Preis
  (noch nicht geprüft). Dateinamen/Struktur uneinheitlich über die Jahre
  (teils mehrere Resultate-PDFs pro Auktion = eine pro Seite, z.B. Juni
  2016 mit 20 Einzeldateien; doppelte Dateien mit "(1)"-Suffix;
  xls/xlsx-Mix).
- [ ] **Entscheidung: zurückgestellt** — nicht wegen Format-Schwierigkeit
  (das ist hier tatsächlich gut lösbar!), sondern wegen Session-Länge und
  der Uneinheitlichkeit über ~13 Jahre, die sorgfältiges Jahr-für-Jahr-
  Vorgehen braucht statt eines einzigen generischen Parsers. Nächster
  logischer Startpunkt für eine Folge-Session: ab 2014 (xls+PDF-Tabelle,
  am einfachsten), dann rückwärts zu 2009-2013 (nur-PDF, Umfang prüfen).

### 6. Weinboerse — ⏸ erster Blick positiv, noch nicht begonnen
- [x] Erste Ergebnis-PDF geprüft (`89_Resultate.pdf`, 2014): **Name UND
  Preis stehen in DERSELBEN Tabelle** (2-spaltig, "Lot | CHF | Anz. |
  Jahr | Beschreibung", Produzent als Fliesstext-Zwischenüberschrift
  oberhalb mehrerer Lots) — kein Zwei-Dokumente-Join nötig wie bei
  Koppe/Sothebys, strukturell näher an Steinfels. Dateinamen aber sehr
  uneinheitlich über die Jahre ("89_Resultate.pdf", "WB 89.pdf",
  "wb-91.pdf", teils "Gebote"-xls = Gebote, nicht Resultate, später
  kombinierte "Resultate©Katalog"-PDFs).
- [ ] **Entscheidung: zurückgestellt** — Format sieht lösbar aus (gute
  Nachricht für die Folge-Session), aber Dateinamen-Chaos über die Jahre
  braucht ebenfalls sorgfältige Jahr-für-Jahr-Arbeit, nicht in dieser
  ohnehin schon sehr langen Session begonnen.

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
