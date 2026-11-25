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

### 5. Steinfels — ✅ erledigt (63 Auktionen, 2004-2020, 97.319 neue Lots)
- [x] **Umfang deutlich grösser als beide ursprünglichen Schätzungen**
  ("~54 Auktionen #325-378 2004-2015" bzw. der revidierte "ab 2014"-Plan):
  die traditionelle Saal-Auktionsreihe (eigene Nummerierung, parallel zur
  2016+ "eAuktion"-Online-Plattform, die bereits vom bestehenden
  `_load_weinauktion_json`/`_load_steinfels_resultfile_json`-Loader erfasst
  wird) läuft nicht nur bis 2015, sondern **durchgehend bis September
  2021** (#325-401) — erst danach ausschliesslich Online-Plattform.
  Vollständig gesichtet: 325-395 ergeben **63 wiederherstellbare
  Auktionen** (29x "bar" nummeriert 2004-2009 ohne eigenen Resultate-
  Dateinamen, 34x mit "Resultate"/"Ergebnis"-Namen 2009-2020), alle mit
  dem GLEICHEN einfachen Tabellenformat (`[Lot Nr.] Produkt Menge Jahrgang
  Zuschlag`, pdftotext -layout reicht, kein Sothebys-artiges Zwei-
  Dokumente-Problem — Lotliste/Katalog werden für die Haupt-Extraktion
  gar nicht gebraucht, nur als Datums-Beleg, siehe unten).
- [x] **Generischer Parser gebaut** (`_steinfels_legacy_pdf_rows`): Spalten-
  Positionen werden PRO SEITE frisch aus der jeweils wiederholten
  Header-Zeile ermittelt (nicht als fixer Offset angenommen) — **echter,
  gefundener Bug dabei**: `pdftotext` hängt das Seitenumbruch-Formfeed-
  Zeichen direkt vor den Zeilenanfang der nächsten Seite, ohne Zeilen-
  umbruch dazwischen — das verschiebt die aus der Header-Zeile gelesenen
  Spalten-Offsets dieser Seite um 1 Zeichen nach rechts gegenüber den
  (unverschobenen) Datenzeilen darunter und hätte sonst auf JEDER
  Folgeseite (ab Seite 2) praktisch alle Zeilen als "nicht parsebar"
  verworfen. Gefixt durch `out.replace("\x0c", "\n")` vor dem Parsen.
  Batch-verifiziert gegen alle 63 Dateien: 0 "bad lines", 0 Lot-Nummer-
  Duplikate pro Auktion.
- [x] **Datierung ohne Tagesgenauigkeit im Dateinamen/Header gelöst über
  Primärquelle, nicht Metadaten-Raten**: für die neuere "Ergebnisliste
  Auktion NNN"-Kopfzeile (2016+) fehlt das Datum; gelöst über die
  gepaarte Katalog-PDF ("Samstag, DD.M.YYYY"). Für 3 Auktionen (372, 375,
  376) fehlte auch das — gelöst über die JEWEILS VORANGEHENDE Auktion's
  eigenen Katalog, der die nächsten 1-4 geplanten Termine nennt ("Die
  nächsten Auktionen sind wie folgt geplant: Samstag, 14. Juni" in 371's
  Katalog → 372 = 2014-06-14 usw.) — eine PDF-Erstellungsdatum-Vermutung
  stimmte hier zufällig exakt überein, wurde aber nur als Bestätigung
  genutzt, nicht als alleinige Quelle (siehe Weinboerse unten, wo genau
  diese Vermutung bei einer Auktion NACHWEISLICH falsch gelegen hätte).
  355 ist ein echter, geprüfter Quellen-Widerspruch (Dateiname
  "13032010" = Samstag, Header-Text selbst sagt "Sonntag, 14. März 2010")
  — Dateiname/Samstag-Konvention übernommen, Diskrepanz dokumentiert statt
  stillschweigend eine Variante gewählt.
- [x] **2 Auktionen in dieser Serie bewusst NICHT aufgenommen** (gleiche
  Güteklasse Entscheidung wie Sothebys/Koppe-Zurückstellung): 371
  (08.03.2014) — einzige "Resultate"-Datei ist eine reine Lot/CHF-Tabelle
  OHNE Weinnamen, bräuchte einen Join gegen die eigene Lotliste-xlsx
  (gleiches Zwei-Dokumente-Problem wie Sothebys/Koppe, nur für 1 Auktion
  statt ~10/40); 380 (11.06.2016) — der "Resultate"-Ordner (23 Dateien)
  ist keine Ergebnistabelle, sondern ein Browser-Screenshot-zu-PDF der
  Lot-Suchseite, UND zeigt bei genauer Prüfung Inhalt der FALSCHEN Auktion
  (381 statt 380) — die Aufnahme selbst ist unzuverlässig, nicht nur
  anders formatiert. 378 (21.11.2015) hat einen Katalog, aber nachweislich
  keine Resultate-Datei im Archiv — kein Parser-Fund, echte Lücke.
- [x] **Senior-Review (automatisch vor Commit) fand 2 echte Befunde:**
  (1) Lots, bei denen das Produkt-Feld selbst z.B. "1975-1982 mixed" oder
  "CHAMPAGNE mixed" lautet (mehrere verschiedene Weine/Jahrgänge als ein
  Lot), wurden als normales Einzelwein-Lot gespeichert, `mixed_lot` blieb
  leer — gefixt über eine zusätzliche `\bmixed\b`-Erkennung im Namen
  (3.838 von 97.319 Lots betroffen, jetzt korrekt geflaggt). (2) Lange
  Produktnamen werden bei manchen Lots an der Spaltenbreite abgeschnitten
  (z.B. Auktion 379 Lot 14: "...Grand Cru Saint-Emili" ohne das
  abschliessende "on") — **geprüft und bestätigt als echte
  Quell-PDF-Begrenzung, nicht behebbar**: mit `pdfplumber`'s Wort-
  Positionen direkt nachgewiesen, dass der Text "on" im PDF selbst gar
  nicht existiert (nicht nur von `pdftotext -layout` verschluckt) — exakt
  dieselbe Klasse von Befund wie bei den 2004-2008-Dateien schon bekannt,
  jetzt bestätigt dass es die GANZE Serie betrifft, nicht nur die alten
  Jahre. Dokumentiert, nicht fixbar (keine Daten zum Wiederherstellen).
- [x] **Sanity-Check** (in-memory gegen das echte Archiv, inkl. der
  bestehenden `load_steinfels`/`load_steinfels_staging`-Loader davor):
  **97.319 neue Lots über 63 Auktionen**, `PRAGMA integrity_check` ok,
  0 Lot-Nummer-Duplikate innerhalb einer Auktion (ausser einem bereits
  VOR dieser Session bekannten, unveränderten Altfall im 2002er-
  Staging-Sheet). Fill-Raten: Weinname 99.998%, Preis 85% (Rest
  nachvollziehbar unverkauft/zurückgezogen wie bei Koppe/Pandolfini),
  Jahrgang 87%, Menge 99%. Stichproben (384 Lot 1/70/77, 325 Lot 1/31)
  Zeile für Zeile exakt gegen den Rohtext verifiziert.
- [x] **Kollisions-Sonderfall 379 korrekt behandelt**: Auktion 379
  (05.03.2016) ist bereits UNVOLLSTÄNDIG über `load_steinfels_staging`
  geladen (464 von real 2062 Lots, gleiche `auction_id`) — statt eines
  pauschalen Datums-Dedup (wie bei MunichWineCompany) wird hier gezielt
  gegen die bereits vorhandenen `lot_no`s unter genau dieser `auction_id`
  dedupliziert. **Ein pauschales Datums-Dedup wäre hier nachweislich
  falsch gewesen**: Auktion 393 (2019-08-31) teilt sich ihr Kalenderdatum
  zufällig mit einer GÄNZLICH ANDEREN, kleineren Online-Auktion
  ("eAuktion 39", 217 Lots) — beide wurden korrekt als getrennte
  Auktionen geladen, geprüft über die jeweilige `auction_id`, nicht das
  Datum.

### 6. Weinboerse — ✅ erledigt (13 Auktionen, 2010-2019, 17.493 neue Lots)
- [x] **Format schwieriger als der erste Blick vermuten liess**: anders
  als Steinfels ist die Ergebnis-Tabelle ZWEI-SPALTIG (zwei komplette
  "Lot CHF Anz. Jahr Beschreibung"-Tabellen nebeneinander auf jeder
  Seite), mit Produzent als eigener Fliesstext-Zwischenüberschrift
  OBERHALB mehrerer Lots (nicht Teil der Tabelle) UND Fällen, in denen
  Menge/Jahrgang/Beschreibung eines Lots komplett auf die nächste Zeile
  umbrechen (nicht nur die Beschreibung). Trotzdem kein Zwei-Dokumente-
  Join nötig (Name+Preis in derselben Tabelle) — das unterscheidet es
  von Koppe/Sothebys.
- [x] **Generischer 2-Spalten-Parser gebaut** (`_wb_legacy_split_halves`
  + `_wb_legacy_parse_stream`): jede Seite wird anhand der zweiten
  "Lot"-Kopfzeilen-Position in zwei unabhängige, einspaltige Zeilen-
  Ströme zerlegt, die dann je für sich wie eine normale Tabelle verar-
  beitet werden. **Senior-Review (automatisch vor Commit) fand und
  bestätigte mehrere echte, nicht offensichtliche Bugs**, alle vor dem
  Commit gefixt und gegen das komplette 13-Auktionen-Set erneut
  verifiziert:
  - Produzenten-Kopfzeilen-Erkennung über GROSSSCHREIBUNG (erster
    Versuch) ist nachweislich falsch — "DOMAINE D'AUVENAY (Leroy)" und
    "ARTHUR BAROLET et Fils" sind echte Produzenten-Zeilen mit
    Kleinbuchstaben; über Einrückung (Spalte 0 = Kopfzeile, eingerückt =
    Beschreibungs-Fortsetzung) gelöst statt über Fallunterscheidung.
  - CHF-Tausendertrennzeichen ist manchmal ein Leerzeichen statt Apostroph
    (z.B. "1 140" = CHF 1140) — ohne Fix wurde das als "Preis=1,
    Menge=140" fehlinterpretiert und hat die GANZE Zeile falsch
    zerlegt. Gefixt über eine 3-Ziffern-Fortsetzungsregel (eine echte
    Mengenangabe ist praktisch nie 3-stellig).
  - Format-Kürzel-Liste war unvollständig (nur Fl./MG/DM/Div./Imp./Jero.
    angenommen) — echte Gegenprüfung über den gesamten Korpus fand auch
    IMP/IM, JER, ME (Melchior), BAL/BA (Balthazar); fehlende Kürzel
    führten dazu, dass die GANZE Zeile beim Fehlen eines Treffers als
    Produzenten-Kopfzeile fehlklassifiziert und das Lot komplett
    verworfen wurde (vor dem Fix: 14-32% "fehlende" Lot-Nummern pro
    Auktion, nach Prüfung gegen den Rohtext ALLE echte Parserfehler,
    keine echten Lücken).
  - Eine seltene (~0.5% der Lots), nicht zuverlässig auflösbare
    Spalten-Kollision (Preis- und Mengen-Ziffern ohne Leerzeichen
    zusammengeklebt, z.B. "3006 MG" = CHF 300/6x ODER CHF 30/06x —
    beides plausibel) wird jetzt erkannt und Lot-Nr./Einheit/Jahrgang/
    Beschreibung trotzdem gespeichert, Preis/Menge bewusst NICHT geraten
    (`None` statt eine falsche Zahl).
  - **Bug nach der Review selbst gefunden und gefixt** (Dict-Key-
    Mismatch: `"fl.": ...` in der Grössen-Tabelle vs. `.rstrip(".")`
    beim Lookup, der den Punkt vorher entfernt) — hat **bottle_size_dl
    für JEDE "Fl."-Zeile (den mit Abstand häufigsten Fall, >9000 Lots)
    auf `None` gesetzt**, obwohl alles andere korrekt war.
  - **2. Senior-Review-Runde fand 2 weitere echte, mit echten Zahlen
    belegte Befunde:** (1) Die Anz.-Spalte erlaubt (wie bei Steinfels)
    einen angehängten Grössen-Bruch ("24 3/8" = 24 Flaschen à 3/8-Liter)
    — der Code prüfte dafür nur `unit`, nicht `anz` selbst, wo der Bruch
    beim Fehlen eines Buchstaben-Kürzels tatsächlich landet (707 von
    17.493 Lots, 4%) — `bottle_size_dl` blieb für alle 707 `None` statt
    3.75dl. (2) Bei "JER" (Jeroboam) wurde blind zwischen Bordeaux-
    (50dl) und Champagne-Konvention (30dl) geraten, obwohl die
    tatsächliche Grösse praktisch immer direkt in der Beschreibung
    steht ("4.5L, OHK...") — bei allen 10 geprüften "4.5L"-Fällen wurde
    fälschlich 50dl statt der korrekten 45dl vergeben. Beide gefixt
    (Bruch aus `anz` extrahieren, explizite "NL"-Grösse vor der
    Konventions-Vermutung lesen) und erneut verifiziert: `bottle_size_dl`
    Fill-Rate jetzt 98% (vorher 94%, vor dem ersten Fix 0%).
- [x] **3 weitere Auktionen geprüft und als NICHT wiederherstellbar
  bestätigt** (keine Annahme, echte Dateiprüfung): 79 (13.11.2010) ist
  entgegen dem ersten Eindruck (Dateiname "79.pdf" sah wie ein Resultate-
  File aus) tatsächlich NUR ein 48-seitiger Vorverkaufskatalog, keine
  einzige Ergebnis-Tabelle enthalten; 81 (Resultate-Datei ist
  byte-identisch mit Auktion 80's eigener Datei — eine echte
  Archiv-Verwechslung, nur die separate "Nachbörse"-Restposten-Liste mit
  Ausrufpreisen statt Zuschlägen liegt für 81 vor, nicht verwendet); 85
  und 90 sind beide reine Auktionskataloge ohne zugehörige Resultate-
  Datei. 95 und 100 haben nur leere "Gebote"-Vorlagen (0 bzw. 6 von
  ~1500 Zeilen mit echtem Gebot, der Rest reine Formular-Nullen) — kein
  echtes Ergebnis archiviert.
- [x] **Datierung**: wie bei Steinfels wo möglich über Primärquelle
  bestätigt (Katalog/Ankündigung mit explizitem Datum für 86, 87, 91, 96,
  98, 99), sonst über PDF-Erstellungsdatum zurückgerechnet auf den
  vorherigen Samstag (dem einzigen Auktionstag dieses Hauses) — diese
  Heuristik wurde an den 5 primärquellen-bestätigten Fällen exakt
  nachgewiesen (0 Abweichung), bevor sie für 78/80/82/84/89/101
  (keine Primärquelle verfügbar) verwendet wurde. **Auktion 93 ist ein
  echter, dokumentierter Quellen-Konflikt**: Auktion 90's eigener
  Katalog (14 Monate im Voraus gedruckt) plante 93 für "05.09.2015",
  aber 93's eigene Ergebnis-Datei wurde laut Metadaten erst "Do 3. Dez
  2015" erstellt — eine 3-Monats-Lücke, die zu JEDER anderen Auktion
  dieses Hauses (durchgehend 1-5 Tage Erstellungs-Verzug) im Widerspruch
  steht. Das metadaten-gestützte Datum (28.11.2015) wurde übernommen,
  die Unsicherheit im Code dokumentiert statt stillschweigend eine
  Variante zu wählen.
- [x] **Kollisions-Check**: `load_weinboerse_legacy` nutzt bewusst das
  Präfix `legacy-` statt der blossen Haus-Auktionsnummer — Auktion
  "101" (diese Session, "WB 101" vom 09.11.2019) hätte sonst exakt mit
  der schon vorhandenen `auction_id="101"` der bestehenden Plattform-
  Loader-Zählung kollidiert, die aber eine GÄNZLICH ANDERE, 2024er
  Auktion ("WB 111", 09.11.2024) ist — ohne Präfix wären zwei echte,
  unabhängige Auktionen über `add_auction`s INSERT-OR-IGNORE-Fallback
  stillschweigend verschmolzen worden.
- [x] **Sanity-Check** (in-memory gegen das echte Archiv): **17.493 neue
  Lots über 13 Auktionen**, `PRAGMA integrity_check` ok, 0 Lot-Nummer-
  Duplikate. Fehlende Lot-Nummern pro Auktion (0-0.3% nach allen Fixes)
  Stichprobe für Stichprobe gegen den Rohtext verifiziert als echte,
  im Haus selbst zurückgezogene Nummern, keine Parser-Fehler. Fill-Raten:
  Weinname 90%, Produzent 99.6%, Preis 99.4% (98 ambige Spalten-
  Kollisionsfälle bewusst ohne Preis/Menge gespeichert statt geraten),
  Jahrgang 88%, Menge 99.4%, Grösse 98%. Stichproben (Lot 1/2/9 von
  Auktion 89, Lot "0" von Auktion 82) Zeile für Zeile gegen den Rohtext
  verifiziert.

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
