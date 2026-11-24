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
> **Arbeitsweise (zwingend, user-vorgegeben):** Strikt sequenziell, ein Punkt
> nach dem anderen. Ein Punkt gilt erst als erledigt, wenn (a) die Daten
> wirklich verarbeitet/gefixt sind, (b) ein Sanity-Check das mit echten
> Zahlen belegt, (c) Senior-Review vor Commit durchlaufen ist
> ([[feedback_senior_review_before_commit]]). Erst dann der nächste Punkt.
> Reihenfolge innerhalb einer Phase ist ein Vorschlag (aufsteigende
> Komplexität, um das Sanity-Check-Muster günstig zu etablieren), kein Dogma.

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

### 1. Pandolfini — kleinster Fall, 2 Auktionen (2015/2016)
- [ ] Rohdateien: `Pandolfini/Result_1-5.html` (+ ggf. weitere), `Catalogo_vini_*.pdf`, `sold-unsold-list-2015.pdf`
- [ ] Bestätigt: `Result_1.html` enthält echte Lot/Preis-Zeilen ("Lot 2 … 1.920" etc.)
- [ ] Auktionsdaten: 15.04.2016 und 11.12.2015
- [ ] Parser schreiben, Sanity-Check gemäss Schema oben, committen

### 2. Sothebys — ~15–20 Auktionen, 2011–2015
- [ ] Rohdateien: 32 `.pdf` + 1 `.webarchive`, u.a. L11710–L15713, N08725/N08797, HK0365–0368
- [ ] Bestätigt: `L11710-Results.pdf` ~140 Lots, GBP
- [ ] Parser schreiben, Sanity-Check, committen

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
