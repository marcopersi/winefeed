# Bauplan: Schutz der eigenen Daten & API gegen Bots, Scraper und AI-Modelle

## 1. Summary

Wir haben Wochen in Erschliessung, Ingestion, Cleansing und Structuring der
Auktionspreis-Datenbasis investiert (22 Häuser, Millionen Zeilen,
`docs/price-prediction-plan.md`s gesamte Preis-Prognose-Pipeline baut
darauf auf). Dieser Plan sichert dieses Ergebnis gegen Abfluss ab: kein
Bot, Scraper, Konkurrent oder AI-Trainings-Crawler soll die Rohdaten
rekonstruieren können — weder über die API noch über das, was der Browser
cleartext ausliefert.

**"Zero Tolerance" muss definiert werden, um ein Abnahmekriterium zu sein
(D1).** Die wörtliche Lesart — "niemand kann je irgendetwas extrahieren" —
ist technisch unerreichbar: Wir selbst haben in den letzten Wochen 22
Häuser mit camoufox gegen Azure-WAF, einer Residential-IP gegen Sothebys
und gelöstem Turnstile gescraped. Ein ähnlich ausgestatteter Angreifer
rekonstruiert aus genügend Browser-Renderings irgendwann alles, was
gerendert wird. Die **erreichbare** Lesart, die "zero tolerance" ehrlich
einlöst: **die Rohdaten (einzelne Lose, exakte Preise, exakte Daten)
verlassen den Server NIE, an NIEMANDEN — auch nicht an zahlende Kunden.**
Ausgeliefert werden ausschliesslich abgeleitete/aggregierte Produkte
(Indizes, Bänder, die Stufe-5-`price_forecasts`-Ausgabe aus dem
Preis-Prognose-Plan, zeitlich/preislich geglättete Punkte). Alles andere
— Rate-Limits, Bot-Erkennung, Verträge — macht Extraktion teuer und
nachweisbar, verhindert sie aber nicht absolut. Das ist die Grenze, gegen
die dieser Plan baut, nicht gegen die unerreichbare.

**Scope-Trennung (wichtig für die Massnahmen):** "Bots" (Scraper,
Harvester, Account-Farmen) sind ein Transport-/Verhaltens-Problem (Rate,
Enumeration, Fingerprint) — Stufe 1/3. "AI-Modelle" als
Trainings-Crawler sind ein anderes Problem (robots.txt/llms.txt,
Cloudflare-AI-Bot-Regeln, ToS) — Stufe 6. Beide Kategorien brauchen
zusätzlich Stufe 4 (Daten-Shaping), weil die eigentliche Verteidigung
ist, was der Server überhaupt herausgibt — nicht, wer fragt.

**Umsetzung:** Dieser Bauplan wird (wie das Preis-Prognose-Projekt) von
einem anderen Modell (deepseek) implementiert; Review durch Claude
(ggf. ein fortgeschritteneres Modell), nach demselben Verfahren wie
`docs/price-prediction-plan.md`s §7. Dieses Dokument selbst enthält noch
keinen Code — es ist die Review-Stufe vor jeder Umsetzung.

---

## 1a. Fortschritts-Übersicht (Stand 2026-11-20)

| Stufe/Schritt | Status |
|---|---|
| 0.1 Exposure-Inventar | 🟡 teilweise — Kern-Inventar in diesem Dokument erstellt (siehe §2), Supabase-Live-Status **jetzt dringlicher** (D4-Tendenz: Supabase Cloud als Produktions-DB) |
| 0.2 Angreifer-Modell | 🟡 Baseline dokumentiert (§2), Abuse-Case-Katalog noch nicht formal ausgeschrieben |
| 0.3 STRIDE/Abuse-Case-Matrix | ⬜ nicht begonnen |
| D1 Zero-Tolerance | ✅ entschieden 2026-11-13, inkl. Nutzer-Zusatz (Prävention + Detektion) |
| D2 Zugriffsstufen | ✅ entschieden 2026-11-13 |
| D3 Öffentliches API? | ✅ entschieden 2026-11-13: nein, nur eigene UI |
| D4 Edge/WAF-Anbieter | 🟡 Tendenz genannt (Supabase Cloud + Cloudflare/netcup), nicht final |
| D5 Rechtliche Durchsetzung | 🟡 Eigentümer geklärt (Nutzer); 6.1.1 (`docs/database-investment-memo.md`) + 6.1.2 (`docs/tos-anti-scraping-clause.md`, v0.2) erledigt, Rechtsberatungs-Review (6.1.4) offen |
| Stufe 0 (vendor-agnostischer Teil)/2/3/4 | ⬜ können beginnen, sobald 0.1 (Supabase-Audit) + 0.3 abgeschlossen sind |
| Stufe 1.2 (WAF) + Deployment | ⬜ blockiert auf finale D4-Entscheidung |

---

## 2. Established Facts (live gegen den Code verifiziert, 2026-11-13)

**Heutiger Live-Exposure-Stand — `api/main.py` (FastAPI, 118 Zeilen):**
- **Kein Auth, kein Rate-Limit, keine Autorisierung.** Jeder der 3
  Endpunkte ist ohne Identität, ohne Token, ohne Quote aufrufbar.
- `CORSMiddleware` erlaubt nur `http://localhost:5173` — das ist eine
  reine Browser-Komfort-Einstellung, **keine Sicherheitskontrolle**: ein
  `curl`/`requests`/Agenten-Call ignoriert CORS vollständig (siehe G1 in
  §4).
- `GET /wines/{wine_id}/prices` liefert die **volle, ungekürzte
  Rohpreis-Zeitreihe** einer Serie: Datum, exakter Preis, Währung,
  Haus-Name, Auktionsort — kein Limit, keine Aggregation, keine
  Tarifstufe.
- `wine_id` ist eine fortlaufende Integer-Primärschlüssel-Spalte. Ein
  simples `for i in range(1, N): GET /wines/{i}/prices` deckt die
  **gesamte** Datenbasis ab — keine Enumerations-Hürde, kein Rätselraten
  nötig. `GET /search?q=` ist zusätzlich ein Name→ID-Oracle, falls IDs
  je verschleiert werden.
- `GET /wines/top?n<=50` und `/search?n<=100` begrenzen nur die
  Antwortgrösse EINES Calls, nicht die kumulierte Menge über viele Calls.

**`price-service-ui`** (React/Vite-SPA, `axios`): ruft `/search`,
`/wines/top`, `/wines/{id}/prices` über relative Pfade auf — kein Token,
kein Session-Handling im Client. Reiner Durchreicher der obigen API.

**Noch nicht öffentlich deployed.** Repo-weite Suche nach
`Dockerfile`/`fly.toml`/`vercel.json`/`docker-compose*`/`Procfile`
ergab **keinen Treffer** — die API läuft heute nur lokal (`uvicorn`) und
die UI nur über `vite dev`. **Das ist der entscheidende Hebel dieses
Plans:** Härtung kann VOR dem ersten Live-Gang entstehen, nicht als
Incident-Response auf einen bereits erfolgten Abfluss.

**`priceData/supabase/`** — ein eigenständiges Supabase-Projekt mit
Migrations (`create_wine_tables`, `create_wine_domain_model`,
`simplified_wine_schema`, `add_reference_tables`, …) und einer
`.branches/_current_branch` (`main`). `priceData/supabase_config.py`
liest `SUPABASE_URL`/`SUPABASE_ANON_KEY`/`SUPABASE_SERVICE_ROLE_KEY` aus
Env-Variablen, **Default-URL ist `http://localhost:54321`** (lokaler
Supabase-CLI-Standardport) — kein im Repo sichtbarer Beleg für ein
verlinktes REMOTE-Projekt, aber auch kein Beleg für das Gegenteil (Keys
liegen per Definition nicht im Repo). **Offen, muss in 0.1 vom
Projekt-Owner bestätigt werden:** existiert ein live/remote
Supabase-Projekt mit echten Daten? Falls ja: welche RLS-Policies hat der
`anon`-Key? Ein zu permissiver `anon`-Key würde jede andere Massnahme in
diesem Plan umgehen, weil er einen zweiten, parallelen Lesezugang auf
dieselben Daten darstellen könnte.

**`priceservice`** (Java/Spring, Gradle) — **kein REST-Controller
irgendwo im Code** (`@RestController`/`@GetMapping`/… ergab keinen
Treffer in `priceservice`, `VinoDomain`, `VinoImporter`, `PersiCommons`).
Es ist ein reiner lokaler Excel→DB-Importer
(`WineAuctionImportRunner`/`ExcelWineReader`), verbunden gegen
`jdbc:postgresql://localhost:5432/winefeed` mit den Default-Credentials
`postgres/postgres` (`application.properties`). Kein öffentlicher Server
heute — aber auf der Inventarliste, falls das je geändert wird, und die
Default-Credentials sind unabhängig davon ein Finding (0.1).

**`.github/workflows/ingest.yml`** lädt rohe Haus-JSONs als
`auction-archive`-Artifact hoch (siehe `docs/price-prediction-plan.md`-
Kontext). Exposure-Risiko nur, falls das Repo öffentlich ist/wird —
Status in 0.1 zu klären, nicht Teil dieses Dokuments.

**Eigene Angreifer-Fähigkeiten als realistische Baseline (§3's D1
begründend):** `ingest/fetchers/` enthält 22 Häuser-Scraper, darunter
camoufox gegen eine Azure-WAF-JS-Challenge (`sylvies.py`), eine
Residential-IP gegen Cloudflare Turnstile (`sothebys`, laut
`AGENTS.md` nur lokal lauffähig), und robuste Pagination-Heuristiken
gegen Server, die aktiv versuchen, Bots zu verwirren (z. B.
`bestwineauctions.py`s Clamp-Erkennung gegen endlos wiederholte
Pager-Seiten). Jede Massnahme in diesem Plan muss gegen diese
Fähigkeiten bestehen, nicht gegen einen naiven `requests.get`-Scraper.

---

## 3. Entscheidungen (D-Nummern, blockieren Gate G0)

| # | Entscheidung | Empfehlung | Begründung |
|---|---|---|---|
| D1 | Zero-Tolerance-Definition | **Entschieden (2026-11-13):** Rohdaten verlassen den Server nie, an niemanden — auch nicht an zahlende Kunden; nur abgeleitete/aggregierte Produkte werden ausgeliefert. **Nutzer-Zusatz:** vollständige Enumeration ist technisch nicht zu 100% verhinderbar, muss aber zuverlässig FESTGESTELLT werden (Rate-Limit pro User/IP, Stufe 3) — Prävention UND Detektion, nicht Prävention allein | Siehe §1 — die wörtliche Lesart ist technisch unerreichbar, diese Lesart ist die einzige testbare und erreichbare |
| D2 | Zugriffsstufen | **Entschieden (2026-11-13):** mind. 3 Stufen: anonym / registriert / paid (+ intern für eigene Dienste) | Ohne Stufen ist Daten-Shaping (Stufe 4) nicht entscheidbar — jede Stufe braucht eine eigene Granularitäts-Grenze |
| D3 | Öffentliches API-Produkt? | **Entschieden (2026-11-13): NEIN — nur die eigene UI (`price-service-ui`) ist Konsument, es gibt kein Dritt-Kunden-API-Produkt.** | Vereinfacht Stufe 2 erheblich: Identität ist Login-Session der eigenen Nutzer, kein Self-Service-API-Key-Issuing, keine B2B-Verträge/SLAs nötig |
| D4 | Edge/WAF-Anbieter | **Noch offen, Tendenz genannt (2026-11-13):** DB vermutlich Supabase Cloud, Applikation vermutlich Cloudflare und/oder ein eigener Mini-Server bei netcup — noch nicht final entschieden | Kostenpflichtige/vertragliche Entscheidung, hier nicht vorwegzunehmen. **Wichtig:** falls Supabase Cloud tatsächlich die Produktions-DB wird, macht das 0.1's RLS-Policy-Audit zur Pflicht-Voraussetzung, nicht zur Kann-Prüfung (siehe 0.1) |
| D5 | Rechtliche Durchsetzung | **Eigentümerfrage geklärt: Nutzer selbst.** Inhaltliche Klärung siehe Chat-Antwort 2026-11-13 (ToS-Anti-Scraping-Klausel, DMCA-Takedown bei US-Hosting, UWG + Datenbankschutzrecht sui generis als vermutlich stärkster Hebel für diesen Fall). **Geklärt (2026-11-14):** Claude liefert den ersten ToS-Klausel-Entwurf als Startpunkt — erstellt als `docs/tos-anti-scraping-clause.md` (v0.1), markiert als nicht rechtsverbindlich. **Korrektur (Copilot-Review, 2026-11-15):** das sui-generis-Datenbankschutzrecht existiert nur EU-rechtlich (Richtlinie 96/9/EG), NICHT nach Schweizer Recht — die Schweiz hat die Richtlinie nie übernommen. In der Schweiz trägt stattdessen das Urheberrecht (Art. 4 URG, falls originell) + UWG; das EU-Recht gilt nur, wenn der Betreiber die Art.-11-Berechtigten-Voraussetzung erfüllt (Sitz/Staatsangehörigkeit in der EU/EWR, nicht blosse EU-Nutzer). Details s. `docs/tos-anti-scraping-clause.md` Ziffer 6(2). | Braucht Rechtsberatung für die finale Fassung (6.1.4); der Entwurf selbst ist kein Blocker für Stufe 1–5 |

**D1–D3 sind entschieden, D4/D5 teilweise offen — Gate G0 ist dadurch
NICHT mehr vollständig blockiert:** die vendor-agnostischen Teile
(Stufe 0/2/3/4 — Identität, Rate-Limiting-Logik, Daten-Shaping) können
beginnen, sobald 0.1–0.3 (Inventar, inkl. der jetzt dringlicheren
Supabase-RLS-Prüfung wegen D4) abgeschlossen sind. Nur Schritt 1.2
(WAF-Konfiguration) und alles Deployment-Spezifische warten auf die
finale D4-Entscheidung.

---

## 4. Guardrails (gelten für ALLE Stufen)

**G1 – CORS ist nie eine Kontrolle.** Eine CORS-Konfiguration ist
Browser-Komfort, kein Schutz gegen einen direkten HTTP-Client (curl,
`requests`, einen Agenten). Sie darf in keinem Abnahmekriterium als
erfüllte Massnahme gegen eine in §2/§5.0.3 benannte Bedrohung gezählt
werden.

**G2 – Keine Security-by-Obscurity als Abnahmekriterium.** "Unser Schema
ist nicht dokumentiert" oder "die ID ist schwer zu erraten" zählt allein
nie als Massnahme — nur in Kombination mit einer echten Kontrolle
(Rate-Limit, Auth, Shaping).

**G3 – Theater ist kein Schutz (D1 wörtlich nehmen).** Canvas-Rendering
von Charts, Anti-Devtools-JavaScript, Chart-als-Bild statt Rohdaten im
DOM: alles, was ein Browser rendert, ist durch denselben Browser
extrahierbar. Die einzige echte Verteidigung ist, dass der **Server**
nie mehr als eine tarifgerecht geformte, begrenzte Sicht pro Request
sendet (Stufe 4) — nicht, was der Client damit anstellt, nachdem er sie
hat.

**G4 – Rohdaten verlassen den Server nie (D1).** Jede neue/bestehende
Response wird gegen D1 geprüft: ein automatisierter Test (Grep/Schema)
stellt sicher, dass `lot_id`, exakter `price_per_bottle_eur`/`price`,
exaktes `lot_date` NIE im Response-Body vorkommen — für KEINE Tarifstufe.

**G5 – Jeder neue/geänderte Endpoint durchläuft vor Merge zwei Reviews:**
die Stufe-4-Shape-Checkliste (Granularität passt zur Tarifstufe, D1
eingehalten) UND den bestehenden Senior-Review-Prozess
(`docs/price-prediction-plan.md` §7 — hier referenziert, nicht neu
erfunden).

**G6 – Defense in Depth, kein Einzelschutz.** Ein Fund "X ist ungeschützt"
wird nicht durch "aber Y schützt doch" entwertet, wenn Y nachweislich
umgehbar ist (z. B. Rate-Limit pro IP umgangen durch Multi-IP). Jede
Stufe steht für sich UND in Kombination.

**G7 – Jede Massnahme braucht einen automatisierten Test.** Kein
"sollte eigentlich reichen" — Property-/Lasttest wie im Preis-Prognose-
Plan (dortiges G5).

**G8 – Rückrollbarkeit.** Jede Änderung an Auth-/Rate-Limit-/WAF-
Konfiguration läuft über Config/Migration, nie ein manueller Hotfix
direkt am Edge/Origin ohne Versionierung.

---

## 5. Micro-Steps

Notation wie im Preis-Prognose-Plan: **Aufwand** S ≤ 2 h, M ≤ ½ Tag,
L ≤ 1,5 Tage. **AC** = Abnahmekriterium. Schritte markiert **(Code)**
gehen an deepseek; **(operativ)** sind Nutzer-/Rechts-Aufgaben ohne Code.

### Stufe 0 – Inventar & Bedrohungsmodell (Voraussetzung, vor jedem Code)

**0.1 Exposure-Inventar vervollständigen** (S, Code+operativ)
- Übernimmt §2 als Startpunkt, schliesst die offene Lücke: ist
  `priceData/supabase` ein live/remote Projekt mit echten Daten? Falls
  ja, welche RLS-Policies hat `anon`? Owner-Bestätigung nötig, kein
  Code kann das aus dem Repo allein beantworten.
- AC: Tabelle Komponente × Status (live/tot/unklar) × Beleg, keine Zeile
  "unklar" ohne benannten Klärungs-Owner und Termin.

**0.2 Angreifer-Modell / Abuse-Cases** (S, Code)
- Mind. 5 Abuse-Cases ausschreiben (anonymer Scraper; registrierter
  Free-Account-Harvester mit "menschlich wirkendem" Tempo; AI-
  Trainings-Crawler; Konkurrent mit Account-Farm; Insider, der einen
  gültigen Paid-Key weiterverkauft/-gibt). Jeder Case referenziert die
  eigene Fetcher-Fähigkeit (§2) als Mindest-Angreifer-Niveau.
- AC: Dokument mit den 5 Cases, je Case: Ziel, Mittel, erwarteter
  Ertrag ohne Gegenmassnahme.

**0.3 STRIDE/Abuse-Case-Matrix** (M, Code)
- Matrix: jeder heutige + geplante Endpoint × jede Bedrohungskategorie
  × welche Stufe (1–6) sie abdeckt.
- AC: keine Zelle ohne Massnahme-Verweis oder explizit begründetes
  "akzeptiertes Risiko".

**Gate G0:** D1–D5 vom Nutzer entschieden, 0.1–0.3 abgeschlossen. **Kein
Code vor Gate G0** (anders als im Preis-Prognose-Plan ist hier die
Entscheidungslage selbst der Blocker, nicht die Datenqualität).

### Stufe 1 – Netzwerk/Edge (vor jeder Auth)

**1.1 TLS-only + Origin-Isolation** (S, Code+operativ)
- HTTPS erzwingen (HSTS), Origin (FastAPI-Prozess/DB) nicht direkt aus
  dem Internet erreichbar — nur über Edge/CDN/Reverse-Proxy.
- AC: `curl` direkt gegen Origin-IP/Port von aussen schlägt fehl
  (Firewall/Security-Group), nur die Edge-Domain ist erreichbar.

**1.2 WAF/Bot-Management vor dem Origin** (M, Code+operativ, Vendor
laut D4)
- Managed Bot-Erkennung vor jedem Request an die API.
- AC: ein bekannter Headless-Browser-Fingerprint (Playwright-Default)
  wird im Test-Setup erkannt/geloggt (Nachweis im WAF-Log) — Blocken
  selbst ist Stufe 3's Aufgabe, hier nur Sichtbarkeit.

**1.3 Secrets-Hygiene** (S, Code)
- `priceservice`s `postgres/postgres`-Default entfernen (falls der
  Dienst je ans Netz geht), DB-Credentials nie im Repo, Secret-Scanner
  (z. B. gitleaks) als CI-Schritt.
- AC: CI-Secret-Scan grün; `git log -p` zeigt keine Klartext-
  Credentials in der Historie (vorhandene Historie prüfen, nicht nur
  künftige Commits).

### Stufe 2 – Identität & Tarife

**Terminologie-Hinweis (gilt für Stufe 2–5 unten):** "Key" steht ab hier
durchgängig für die INTERNE Identität — Nutzerkonto-/Session-ID für
registriert/paid, eine anonymisierte Session- oder Device-Kennung für
anonym. Es gibt laut D3 KEINE extern an Dritte ausgegebenen API-Keys;
wer das implementiert, baut Infrastruktur für ein Produkt, das es laut
D3 nicht gibt.

**2.1 Identitäts-Modell** (M, Code, laut D2/D3)
- **D3 entschieden (kein öffentliches API-Produkt):** Identität ist die
  Login-Session der eigenen Nutzer im eigenen Frontend, nicht ein an
  Dritte ausgegebener API-Key — **JWT/Session-Cookie statt opaker
  API-Keys** (die Alternative aus der ursprünglichen Fassung dieses
  Schritts entfällt damit). anonym / registriert / paid (+ intern)
  bleiben die drei(+1) Stufen, nur die Trägerform ändert sich.
- AC: jeder Request ohne gültige Session bekommt die anonyme Stufe —
  nie implizit eine höhere.

**2.2 Session-Rotation/-Revocation** (M, Code)
- Logout invalidiert die Session serverseitig (nicht nur Client-Cookie
  löschen); Pflicht-Ablaufdatum/Refresh-Flow. Kein Self-Service-
  API-Key-Issuing nötig (D3) — Registrierung/Login genügt als
  Identitäts-Grundlage.
- AC: eine invalidierte Session wird binnen der Cache-TTL (konkreter
  Wert im Review festzulegen, nicht "schnell") abgelehnt — Test mit
  Zeitsprung/Mock, nicht Warten in Echtzeit.

**2.3 Tarif-Quoten konfigurierbar** (S, Code)
- Datenmodell für Quoten (Requests/Tag, Unique-Wines/Tag — siehe 4.5),
  nicht hartkodiert im Code.
- AC: Quote änderbar ohne Deploy; Test deckt den Grenzfall (exakt am
  Limit, 1 drüber).

### Stufe 3 – Rate-Limiting & Abuse-Erkennung

**3.1 Token-Bucket pro Key UND pro IP** (M, Code)
- Doppelte Begrenzung: ein Key hinter wechselnden IPs UND eine IP mit
  mehreren Keys müssen beide greifen.
- AC: Property-Test — der (N+1)-te Request im Fenster ist `429`, der
  N-te nicht, für beide Dimensionen unabhängig geprüft.

**3.2 Endpoint-spezifische Limits** (S, Code)
- `/search` (Name→ID-Oracle, §2) enger limitiert als
  `/wines/{id}/prices`.
- AC: Lasttest zeigt, dass `/search` bei niedrigerer Rate blockt als
  `/prices`.

**3.3 Sequentieller-Zugriffs-Detektor** (M, Code)
- Erkennt "ID n, n+1, n+2…"-Muster bzw. systematisches Durchlaufen des
  ID-Raums — die eigene Fetcher-Pagination-Logik (§2) ist hier das
  Vorbild für das, wogegen verteidigt wird.
- AC: synthetischer Walk über 50 aufsteigende IDs in < 5 Min. triggert
  ein Flag; dieselbe Anzahl Requests in zufälliger ID-Reihenfolge
  triggert es nicht.

**3.4 Progressive Challenge** (M, Code)
- PoW → CAPTCHA → Block, gestaffelt nach Verdachts-Score statt hartem
  Cutoff.
- AC: definierter Score-Schwellenwert pro Stufe (Review legt die Werte
  fest, nicht geraten); Test deckt alle drei Übergänge.

**3.5 Response-Delay-Throttling** (S, Code)
- Antwortzeit künstlich erhöhen statt hart blocken bei
  Quoten-Überschreitung unterhalb der Challenge-Schwelle (verlangsamt
  Harvesting ohne legitime Gelegenheitsnutzer zu sperren).
- AC: gemessene Latenz steigt nach Quoten-Überschreitung messbar; Test
  mit Zeit-Mock, nicht Echtzeit-Warten.

### Stufe 4 – Daten-Shaping (Kernstück, D1 wird hier technisch wahr)

**4.1 Opake IDs** (S, Code)
- Sequentielle Integer-`wine_id` durch opakes Token/UUID ersetzen —
  **nicht als alleinige Massnahme** (G2): zusätzlich zu, nicht statt
  Rate-Limiting/Shaping.
- AC: Test über 1000 angefragte IDs — keine fortlaufende/ableitbare
  Struktur nachweisbar.

**4.2 Harte Pagination-Caps, tages-kumuliert** (S, Code)
- Cap nicht nur pro Call (`n<=100`), sondern pro Key/Tag über ALLE
  Calls summiert.
- AC: Test, dass das Tages-Cap durch viele kleine Requests nicht
  umgangen werden kann (Summe wird serverseitig gezählt, nicht pro
  Request neu betrachtet).

**4.3 Tarif-abhängige Aggregation** (L, Code, zentral — hängt an
D1/D2)
- Konkreter Vorschlag (im Review zu bestätigen/anzupassen): anonym =
  nur Monats-Median je Serie; registriert = Wochen-Median; paid =
  tages-granuliert MIT Jitter. **Einzelne Lose/exakte Preise für
  NIEMANDEN über die API (D1).**
- AC: pro Tarifstufe ein Response-Schema-Test, der verifiziert, dass
  die zurückgegebene Granularität nicht unter der Tarif-Grenze liegt;
  zusätzlich ein Property-Test (G4), dass `price_per_bottle_eur` (exakt),
  `lot_id`, exaktes `lot_date` in KEINEM Response-Body vorkommen.

**4.4 Feld-Redaktion** (S, Code)
- `provider`-Name/`location`/exaktes Lot-Datum nicht 1:1 durchreichen —
  ersetzen durch Kategorie/Region/Monat (Granularität wie 4.3).
- AC: Schema-Test wie 4.3, für diese Felder.

**4.5 Unique-Wine-Tagesbudget** (M, Code)
- Zusätzlich zur Request-Rate: Anzahl UNTERSCHIEDLICHER abgefragter
  Weine/Tag pro Key begrenzen — verhindert langsames, Rate-konformes
  Komplett-Harvesting über viele Tage.
- AC: Test mit 1 Request/Minute über 24 h gegen 10 000 verschiedene IDs
  wird trotzdem gestoppt (Zeit-Mock, nicht Echtzeit).

### Stufe 5 – Erkennung & Forensik

**5.1 Canary-Weine** (M, Code+operativ)
- Fiktive, plausible Weine pro Tarif/Key eingestreut; Auftauchen in
  einem fremden Produkt/Dump ist Beweis für ein Leck.
- AC: mind. 1 Canary-Eintrag pro aktivem Key abrufbar, von echten
  Einträgen nicht unterscheidbar (Blind-Test durch einen zweiten
  Reviewer).

**5.2 Statistisches Wasserzeichen** (M, Code)
- Für sich genommen unauffälliges, key-spezifisches Jitter-/
  Rundungsmuster, menschlich nicht erkennbar, aber re-identifizierbar.
- AC: Re-Identifikationstest — aus einem synthetischen "Leck"-Sample
  wird der Quell-Key mit hoher Konfidenz zurückgerechnet.

**5.3 Audit-Log** (S, Code)
- Jeder Request mit Key/IP/Endpoint/Resultgrösse; Aufbewahrungsdauer
  laut Stufe 6.
- AC: ein synthetischer Abuse-Lauf ist im Log nachträglich eindeutig
  rekonstruierbar.

**5.4 Anomalie-Alerting** (S, Code+operativ)
- Schwellenwert-Alarme (Volumen, Unique-Wine-Rate, Canary-Zugriff) an
  einen benannten Kanal/Owner.
- AC: Test-Alarm löst aus, Owner bestätigt Empfang.

**5.5 Takedown-Runbook** (S, **operativ**, kein Code)
- Schritt-für-Schritt-Dokument: Key sperren, Forensik sichern
  (Audit-Log, Canary-Treffer), rechtliche Eskalation (Stufe 6).
- AC: Dokument vorhanden UND einmal tabletop-durchgespielt (simulierter
  Vorfall, kein echter nötig).

### Stufe 6 – Rechtlicher Rahmen (operativ, kein Code)

**6.1 ToS mit Anti-Scraping-/Anti-Training-Klausel** (operativ) — der
Kern-Baustein, auch ohne öffentliches API-Produkt relevant, weil die
eigene Web-UI das Angriffsziel ist. Wirkt nicht präventiv, sondern erst
NACH einer Detektion (Stufe 3) als rechtliche Grundlage für Sperre/
Abmahnung/Klage — Zustimmung muss Clickwrap sein (aktive Checkbox bei
Registrierung), nicht Browsewrap (reine Nutzung), da nur Clickwrap
beweisbare Zustimmung liefert. Zerlegt in:

- **6.1.1 Investitions-Dokumentation** (S, operativ) — internes Memo mit
  konkreten Zahlen (Stunden, Anzahl Häuser/Lots, Pipeline-Komplexität)
  als Beleg für die "wesentliche Investition", die das EU-sui-generis-
  Datenbankschutzrecht voraussetzt (für die Schweiz selbst: Urheberrecht/
  UWG, s. 6.1.2-Korrektur). AC: Memo vorhanden, referenzierbar für eine
  spätere Rechtsberatung. **✅ erledigt 2026-11-14, korrigiert 2026-11-15
  (Copilot-Review)** — `docs/database-investment-memo.md`: alle Umfangs-/
  Komplexitätszahlen live gegen die Produktions-DB und das Repo
  verifiziert (24 Provider, 9'078 Auktionen, 4'297'347 Lose, 3'232'827
  aufgelöste Einzelwein-Lose — davon 970'984 tatsächlich prognosefähig
  nach `forecast_input`s zusätzlichen Eligibility-Filtern, nicht alle
  3'232'827 — 51 Tage/105 Commits Entwicklung); Fetcher-Modulzahl
  (22 Module/23 Provider, idealwine+christies bereits darin enthalten)
  und die CH/EU-Rechtslage korrigiert. Stundenaufwand/direkte Kosten als
  offene Punkte markiert (nur vom Nutzer selbst zu beziffern).
- **6.1.2 Klausel-Entwurf** (M, operativ, Autor: Claude als Startpunkt)
  — Pflichtbestandteile: Definition "automatisierter Zugriff"/
  "Scraping"; separates, explizites Trainings-Nutzungsverbot (inkl.
  abgeleiteter/aggregierter Daten); Anti-Umgehungs-Klausel (Verbot, die
  technischen Schutzmassnahmen aus Stufe 1–5 zu umgehen); expliziter
  Vorbehalt des Datenbankschutzrechts; Rechtsfolgen bei Verstoss
  (Sperre, Schadensersatzvorbehalt); anwendbares Recht/Gerichtsstand.
  AC: Entwurf vorhanden, alle genannten Elemente enthalten, ausdrücklich
  als "nicht rechtsverbindlich, Entwurf für Rechtsberatung" markiert.
  **✅ erledigt 2026-11-14, v0.2 nach Copilot-Review 2026-11-15** — Entwurf
  in `docs/tos-anti-scraping-clause.md` (inkl. Vollständigkeits-Check
  gegen dieses AC als Anhang). v0.2 behebt 3 Findings: (a) die Klausel
  band wörtlich auch gewöhnliche UI-Requests als "automatisierten
  Zugriff" ein, jetzt explizit ausgenommen (Ziffer 1(2)); (b) sie
  beanspruchte Vertragswirkung auch gegenüber der Zugriffsstufe "anonym",
  obwohl dort keine Zustimmungshandlung existiert — jetzt auf
  registrierte/paid-Nutzer begrenzt, anonym bleibt via Datenbankrecht/UWG
  abgedeckt (Ziffer 1(4)); (c) der Datenbankschutzrechts-Vorbehalt
  behauptete fälschlich ein Schweizer sui-generis-Recht, jetzt auf
  Urheberrecht/UWG (CH) bzw. EU-Recht mit Art.-11-Vorbehalt korrigiert
  (Ziffer 6(2)). Nächster Schritt 6.1.4 (Rechtsberatung, Owner: Nutzer).
- **6.1.3 Clickwrap-Integration** (S, Code, an Stufe 2/Login gekoppelt)
  — Pflicht-Checkbox bei Registrierung, kein Vorab-Haken. AC: ohne
  aktive Zustimmung keine Account-Erstellung möglich, UND (Copilot-
  Review-Finding, 2026-11-15) serverseitige, dauerhafte Aufzeichnung der
  Zustimmung je Account — Account-ID, akzeptierte Klausel-Version,
  Zeitstempel — mit dem akzeptierten Versionstext weiterhin abrufbar
  (hängt an 6.1.5s Versionierung), nicht nur eine Checkbox + eine
  separat versionierte ToS-Seite ohne Verknüpfung dazwischen.
- **6.1.4 Rechtsberatungs-Review** (Aufwand offen, operativ, Owner laut
  D5: Nutzer) — AC: Anwalt/Rechtsberatung (Jurisdiktion CH, ggf.
  zusätzlich EU bei EU-Nutzern) hat 6.1.2 freigegeben.
- **6.1.5 Publikation + Versionierung** (S, Code) — eigene Route,
  sichtbares Datum/Versionsnummer, Änderungsprotokoll. AC: live,
  versioniert — für spätere Beweisführung "galt zum Zeitpunkt X".

**6.2 API-Nutzungsvertrag für Dritt-Kunden** — **entfällt (D3: kein
öffentliches API-Produkt, nur eigene UI).**
**6.3 `robots.txt` + `llms.txt`** (S, Code) — **Fact, nicht Annahme:**
beides ist rein advisory (kein technischer Schutz, folgt freiwillig),
aber Teil der rechtlichen Durchsetzbarkeit und Teil von G2's
Nicht-als-alleinige-Massnahme-Logik — hier als Ergänzung zu Stufe 1–5,
nie als Ersatz.
**6.4 DMCA-/UWG-Durchsetzungsprozess** (operativ, Owner laut D5)

AC je Schritt: Dokument vom Nutzer/Rechtsberatung abgezeichnet (6.3
zusätzlich: Datei im Repo, von einem Crawler-Test als vorhanden
bestätigt).

### Stufe 7 – Verifikation (Red-Team, Gate G7)

**7.1 Eigener Fetcher-Stack gegen die gehärtete API** (M/L, Code)
- Derselbe Werkzeugkasten wie gegen die 22 Häuser (Playwright, ggf.
  camoufox, Residential-IP-Pool aus §2) — jetzt gegen die EIGENE API,
  für jede Tarifstufe einzeln.
- AC: dokumentierte Ausbeute (Zeilen/Datenpunkte pro Stunde) je
  Tarifstufe. **Ziel laut D1: 0 Rohdaten-Zeilen extrahierbar, auf
  KEINER Tarifstufe.** Eine gewisse Menge aggregierter Datenpunkte/
  Stunde ist akzeptiert und zu dokumentieren — das ist keine
  AC-Verletzung, sondern das erwartete, bewusst zugelassene Ergebnis
  von D1's "abgeleitete Produkte werden ausgeliefert".

**Gate G7:** Red-Team-Bericht vom Autor (deepseek) **plus unabhängige
Nachprüfung** — ein zweiter Reviewer wiederholt den Angriff selbst,
statt den Bericht zu glauben (dieselbe Adversarial-Check-Logik wie im
Preis-Prognose-Plan §7, Punkt 4). **Kein Go-Live vor Gate G7.**

---

## 6. Senior-Review-Verfahren

Folgt `docs/price-prediction-plan.md` §7 unverändert (Selbst-Check →
mechanischer Review `/code-review high` → Fach-Review → optionaler
Adversarial-Check → Review-Log hier in §7). Ergänzend für diesen Plan:

- **Jeder Endpoint-Review prüft zusätzlich die Stufe-4-Checkliste** (G4:
  D1 eingehalten, Granularität passt zur Tarifstufe) — kein Merge ohne
  diesen Punkt abgehakt, auch wenn der mechanische Review sonst clean
  ist.
- **Gate G7 ersetzt kein normales Review** — der Red-Team-Lauf ist
  zusätzlich zum, nicht statt des Code-Reviews.

---

## 7. Review-Log

| Datum | Gate | Reviewer | Befunde | Entscheid |
|---|---|---|---|---|
| 2026-11-13 | Plan-Erstellung | Claude (Code-Inventur: `api/main.py`, `price-service-ui`, `priceservice`, `priceData/supabase`, `.github/workflows`; Architektur-Gegenprüfung via `advisor`) | Live-Exposure vollständig ungeschützt (kein Auth/Rate-Limit, sequentielle IDs, volle Rohdaten-Ausgabe), aber **noch nicht öffentlich deployed** — kein Dockerfile/fly.toml/vercel.json/docker-compose gefunden. `priceData/supabase`-Live-Status (echtes Remote-Projekt mit Daten? RLS-Policy des `anon`-Keys?) aus dem Repo allein nicht klärbar — als offener Punkt in 0.1 markiert statt geraten. `priceservice` ist ein reiner lokaler Importer, kein öffentlicher Server. | Plan erstellt, D1–D5 dem Nutzer zur Entscheidung vorgelegt (§3), Gate G0 blockiert jeden Code bis zur Klärung. Noch keine Umsetzung. |
| 2026-11-13 | D1–D5 Nutzer-Entscheid | Nutzer (per Chat) | D1 bestätigt, mit Zusatz: vollständige Enumeration ist technisch nicht zu 100% verhinderbar, muss aber zuverlässig per Rate-Limit/User/IP FESTGESTELLT werden (Prävention + Detektion, nicht Prävention allein) — in D1-Zeile (§3) und Stufe 3 reflektiert. D2 bestätigt unverändert. **D3 entschieden: kein öffentliches API-Produkt, nur die eigene UI** — vereinfacht Stufe 2 grundlegend (Login-Session statt extern ausgegebener API-Keys; 2.1/2.2 umgeschrieben, Terminologie-Hinweis "Key = interne Identität" vor Stufe 2 ergänzt, 6.2 als entfallend markiert). D4 noch offen, Tendenz genannt (Supabase Cloud als DB, Cloudflare und/oder netcup-Mini-Server als Applikation) — macht 0.1's Supabase-RLS-Audit dringlicher, nicht mehr nur hypothetisch. D5: Eigentümerfrage geklärt (Nutzer selbst), ToS/DMCA/UWG-Begriffe im Chat erläutert (Datenbankschutzrecht sui generis als vermutlich stärkster Hebel für diesen Fall); offen, ob ein erster ToS-Klausel-Entwurf gewünscht ist. | D1–D3 als entschieden markiert (§3, §1a). Gate G0 nicht mehr vollständig blockiert: vendor-agnostische Teile (Stufe 0/2/3/4) können nach Abschluss von 0.1/0.3 beginnen; nur Stufe 1.2 (WAF) und Deployment-Spezifisches warten weiter auf die finale D4-Entscheidung. Plan-Dokument entsprechend aktualisiert, noch keine Code-Umsetzung. |
| 2026-11-13 | 6.1 Zerlegung | Claude (per Chat: Erklärung ToS/Anti-Scraping/Anti-Training-Klausel, Zusammenspiel mit DMCA/UWG/sui-generis-Datenbankschutzrecht) | 6.1 war ein Einzeiler ohne Umsetzungs-Struktur. Zerlegt in 6.1.1 Investitions-Dokumentation (Beleg für sui-generis-Schutz), 6.1.2 Klausel-Entwurf (Claude als Startpunkt, kein Rechtsrat), 6.1.3 Clickwrap-Integration (Code, an Stufe 2 gekoppelt), 6.1.4 Rechtsberatungs-Review (Owner: Nutzer), 6.1.5 Publikation+Versionierung (Code). | 6.1.1–6.1.5 im Plan ergänzt. 6.1.2 (der eigentliche Klausel-Entwurf) noch nicht geschrieben — nächster Schritt auf Nutzer-Anfrage. |
| 2026-11-14 | 6.1.2 Klausel-Entwurf | Claude (Autor gemäss Plan; auf Nutzer-Anfrage "Bauplan implementieren") | Erster Entwurf der ToS-Klausel erstellt: alle Pflichtbestandteile des 6.1.2-AC enthalten (Scraping-Definition, separates Trainingsnutzungsverbot inkl. abgeleiteter Daten, Anti-Umgehungs-Klausel, Datenbankschutzrechts-Vorbehalt, Rechtsfolgen, Recht/Gerichtsstand), als nicht rechtsverbindlich markiert, mit Vollständigkeits-Check als Anhang. Keine Rechtsberatung — bewusst als Arbeitsgrundlage für 6.1.4 angelegt. | Entwurf in `docs/tos-anti-scraping-clause.md` (v0.1) abgelegt; Fortschritts-Übersicht (§1a D5) und D5-Zeile (§3) aktualisiert. Nächster Schritt: 6.1.4 Rechtsberatungs-Review (Owner: Nutzer); 6.1.3 (Clickwrap) + 6.1.5 (Versionierung) sind Code und gehen an deepseek, gekoppelt an Stufe 2. |
| 2026-11-14 | 6.1.1 Investitions-Dokumentation | Claude (Zahlen live gegen Produktions-DB `/Volumes/samsung/winefeed-data/wine_auction_prices.sqlite` und Repo verifiziert, nicht geraten) | Umfangs-/Komplexitätszahlen ermittelt (24 Provider, 9'078 Auktionen, 4'297'347 Lose, 3'232'827 bereinigte Preisbeobachtungen, 269'884 Wein-Referenzen, 1998–2026 Abdeckung, 3.47 GB; 22 Fetcher-Module/3'848 Zeilen + 5'473 Zeilen Build-Pipeline, 51 Tage/105 Commits Entwicklung; Sothebys camoufox/Residential-IP/Turnstile als Beleg für Nicht-Trivialität). Stundenaufwand/direkte Kosten NICHT aus dem Repo ableitbar — als offene Punkte markiert statt geraten. | Memo in `docs/database-investment-memo.md` abgelegt, 6.1.1 als erledigt markiert (§1a, §5). Offene Punkte (Stunden/Kosten) warten auf Nutzer-Angabe, sind aber kein Blocker für 6.1.4. |
| 2026-11-15 | GitHub-Copilot-PR-Review (PR #112, 6.1-Dokumente) | GitHub Copilot (automatisiert, 6 Findings, alle Low bis auf 1 Medium); Claude verifizierte jedes Finding empirisch (Live-DB-Query, Code-Lektüre, Websuche zur CH/EU-Rechtslage) statt die Einstufung blind zu übernehmen | **Alle 6 Findings verifiziert ECHT:** (1) Die ToS-Klausel beanspruchte Vertragswirkung auch gegenüber der Zugriffsstufe "anonym" (D2), obwohl dort nie eine Zustimmungshandlung stattfindet (2.1 erlaubt anonymen Zugriff ohne Registrierung). (2) 6.1.3s AC verlangte nur eine Checkbox + eine separat versionierte ToS-Seite, ohne serverseitige Verknüpfung welcher Account welche Version wann akzeptierte — nach einem ToS-Update nicht beweisbar. (3) `single_wine_prices` (`data/build_db.py` Zeilen 325–330) filtert nur `lot_kind='SINGLE'`/aufgelöste Referenz/sauberen Jahrgang, NICHT `sold=1`/Preis/Datum — Live-Messung: 3'232'827 Zeilen dort gegen nur 970'984 in `forecast_input` (den tatsächlich eligiblen Zeilen), das Memo nannte die grössere Zahl fälschlich "prognosefähig". (4) Die 22 Fetcher-Module (`ingest/fetchers/__init__.py`) enthalten idealwine UND christies bereits (Live-Code-Lektüre) — das Memo zählte sie fälschlich als zusätzlich zu den 22; zudem bedient `WeinauktionFetcher` zwei Provider (steinfels, weinboerse) gemeinsam, "ein Modul pro Haus" war ungenau (23 Provider/22 Module, live per DB-Query bestätigt; 2 der 24 DB-Provider (`wermuth-sa`, `zacky`) haben gar kein aktives Fetcher-Modul). (5) Die Scraping-Definition (Ziffer 1(2)) erfasste wörtlich auch gewöhnliche React-UI-Requests (`price-service-ui/src/lib/api.js`, axios.get) als "automatisierten Zugriff" — Widerspruch zur erlaubten Plattform-Nutzung (Ziffer 2(1)). (6) **Websuche bestätigt (mehrere unabhängige Quellen, u.a. IGE):** die Schweiz hat die Richtlinie 96/9/EG nie übernommen und kennt KEIN eigenständiges sui-generis-Datenbankherstellerrecht — frühere Fassungen aller drei 6.1-Dokumente behaupteten das fälschlich ("EU/CH"-Recht); zusätzlich bezieht sich die EU-Berechtigten-Voraussetzung (Art. 11 der Richtlinie) auf Sitz/Staatsangehörigkeit des Betreibers, nicht auf die Existenz von EU-Nutzern. | Alle 6 Findings gefixt: `tos-anti-scraping-clause.md` → v0.2 (neue Ziffer 1(4) Vertragsreichweite nach Zugriffsstufe, UI-Ausnahme in Ziffer 1(2), CH/EU-Korrektur in Ziffer 6(2), "Offene Punkte" um Art.-11-Prüfung ergänzt); `database-investment-memo.md` (Header-Korrektur, `single_wine_prices`-Zeile umbenannt + neue `forecast_input`-Zeile mit echter Zahl, Fetcher-Modul-Zeile korrigiert); `data-api-security-plan.md` (D5-Zeile, 6.1.1/6.1.2/6.1.3-ACs). Keine Code-Änderung, reine Dokument-Korrektur. |
| 2026-11-15 | GitHub-Copilot-PR-Review, Runde 2 (PR #113, Folge-Review auf die Fixes der Runde 1) | GitHub Copilot (automatisiert, 2 Findings, beide Low); Claude verifizierte beide empirisch, korrigierte dabei einen eigenen Fehler aus Runde 1 statt ihn stehen zu lassen | **Beide Findings verifiziert ECHT:** (1) Die `forecast_input`-Eligibility-Beschreibung (6.1.1-Korrektur, Runde 1) liess `price_kind IS NULL` (`data/build_db.py` Zeile 404 -- schliesst idealwines COTE-Bewertungen aus, auch bei vorhandenem Preis/Datum) aus und liess die 36-Monats-Regel ("Serie aktiv") unspezifiziert; zudem beruht `series_last_obs >= date('now','-36 months')` auf dem AKTUELLEN Kalenderdatum -- die Zahl 970'984 ist eine Momentaufnahme, keine stabile DB-Eigenschaft, und driftet bei jeder Neuberechnung. (2) **Eigener Fehler aus Runde 1 gefunden:** die Behauptung, `wermuth-sa` habe kein aktives Fetcher-Modul, war falsch -- Live-Code-Lektüre (`data/orchestrate.py` Zeilen 40-45) zeigt, dass der Fetcher-Modul-REGISTRY-Key `denzauktionen` in den DB-Provider `wermuth-sa` schreibt (Nachfolger des historischen Wermuth/Denz-PDF-Archivs) -- Registry-Key und DB-Provider-Name sind hier verschiedene Strings, was Runde 1 übersehen hatte. Nur `zacky` ist tatsächlich unversorgt (`load_zacky`, ein statischer Loader ohne `ingest/fetchers/`-Eintrag). Zusätzlich war "Delta-/Backfill-Mechanismus innerhalb des Fetcher-Moduls" falsch lokalisiert: beide Mechanismen sitzen in eigenen Orchestrierungs-Skripten (`data/run_idealwine_delta.py`, `data/run_christies_backfill.py`), nicht im Fetcher-Modul selbst. | Beide Findings gefixt in `database-investment-memo.md`: `forecast_input`-Zeile um `price_kind IS NULL` ergänzt und explizit als "Momentaufnahme 2026-11-15" markiert; Fetcher-Modul-Zeile korrigiert (wermuth-sa aus der "unversorgt"-Liste entfernt, Registry-Key-vs-Provider-Name-Unterschied erklärt, Delta/Backfill-Skripte korrekt verortet). Keine Code-Änderung. |

---

## 8. Reihenfolge & Aufwand (grob)

Stufe 0: 1–2 Tage (hängt an Entscheidungsgeschwindigkeit D1–D5, nicht an
Code) · Stufe 1: 1–2 Tage · Stufe 2: 2 Tage · Stufe 3: 3–4 Tage ·
Stufe 4: 3–4 Tage (Kernstück, am aufwändigsten) · Stufe 5: 2 Tage ·
Stufe 6: parallel, operativ, kein Blocker für Stufe 1–5 ausser 6.3
(Code) · Stufe 7: 1–2 Tage ⇒ **≈ 3 Wochen** nach Klärung von D1–D5,
wovon Stufe 4 den grössten Hebel hat (D1 wird erst dort technisch wahr)
und Stufe 7 (Gate G7) die einzige Instanz ist, die "zero tolerance"
tatsächlich testet statt behauptet.
