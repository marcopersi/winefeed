# Premium-/Gebühren-Policy je Haus (Ground Truth)

Stand: 2026-11-20. Dies ist die verbindliche Gebührenstruktur je Haus, aus
Primärquellen (Terms/Conditions) zu pflegen. Spalten: Preis-Basis (was der
Fetcher liefert), Buyer's Premium, Fees (Lotgebühr), MwSt/VAT, Quelle.

| Haus | Preis-Basis | Buyer's Premium | Fees | MwSt | Quelle/Status |
|---|---|---|---|---|---|
| sothebys | HAMMER | 24 % + Overhead 1 % (Wines & Spirits) | — | VAT | bestätigt (Help Center) |
| pandolfini | HAMMER_PLUS_BUYERS_PREMIUM | im Preis enthalten | — | — | bestätigt |
| zacky | HAMMER_PLUS_BUYERS_PREMIUM | im Preis enthalten | — | — | bestätigt |
| hdh | HAMMER (`hammer`), `aggregate` inkl. Premium | `aggregate - hammer` | — | — | bestätigt |
| idealwine | (cote, kein Hammer) | 25,2 % TTC bis 26.03.2026, 25,8 % TTC ab 01.04.2026 | — | inkl. TTC | bestätigt |
| christies | HAMMER | 25 % Wine (HK/Asia); non-wine gestaffelt 26/21/15 %; hist. NLG 20,825 % | — | VAT on premium | bestätigt (Conditions of Sale) |
| langtons | HAMMER (`winning_bid`) | 16,5 % (bis 2022), 18 % (ab Feb 2023) | — | GST | bestätigt |
| dorotheum | HAMMER | ~25 % Differenzbesteuerung (inkl. VAT) / 20,84 % Regelbesteuerung | — | VAT | bestätigt (Conditions of Sale) |
| winefields | HAMMER (`hammer`) | 24 % flat (aktuell); 22 %/20 % historisch | — | VAT 21 % (NL) | bestätigt |
| baghera | HAMMER | 22 % flat | — | — | bestätigt (Katalog) |
| steinfels | HAMMER | 12 % + CHF 10/Lot Lotgebühr | CHF 10/Lot | 8,1 % | bestätigt (Bidding-Seite) |
| finarte | HAMMER | 23 % (Wines & Spirits, 18,85 % + VAT) | — | VAT | bestätigt (Conditions of Sale) |
| weinboerse | HAMMER | 15 % + CHF 10/Lot Lotgebühr | CHF 10/Lot | 8,1 % | bestätigt (Katalog) |
| koppe | HAMMER | 10 % | EUR 5/Lot Abwicklungsgebühr | USt auf Aufgeld | bestätigt (Auktionsbedingungen) |
| weinauktionator | HAMMER | 15 % | — | USt | bestätigt (AGB) |
| dobiaschofsky | HAMMER | 25 % (bis CHF 200k) / 22 % (ab CHF 200k) | — | 8,1 % auf Aufgeld | bestätigt (Auktionsbedingungen) |
| wermuth-sa (Denz, Zürich) | HAMMER | 10 % | CHF 8/Lot | 8,1 % | bestätigt (Konditionen) |
| besch-cannes | HAMMER | 24 % (direkt) / 27,6 % (Interenchères) / 25,8 % (Drouot) | — | inkl. MwSt | bestätigt |
| munich-wine-company | HAMMER | 15 % | € 5/Lot | USt | bestätigt |
| winebarrel | — (Konsignations-Service, kein klassisches Aufgeld) | Seller-Provision 7,5–15 % (gestaffelt) | — | — | bestätigt |
| sylvies | HAMMER | 20 % exkl. MwSt | — | zielland-abhängig, kein fixer Satz | bestätigt (sylvies.be Conditions of Sale) |
| whiskyauction | HAMMER | 15 % flat, aktueller Satz auf alle Lots angewandt (keine Staffel, kein Wein/Whisky-Unterschied; ob der Satz für ältere Auktionen (vor 2026) schon galt, ist nicht verifiziert -- gleiche Approximation wie bei langtons/winefields) | — (£5 Registrierung ist Account-, nicht Lot-Gebühr) | zielland-abhängig (UK: +VAT; Rest: keine VAT auf Commission), kein fixer Satz | bestätigt (whisky.auction/our-fees, "Buyers Fees > Commission fee") |
| crait-muller / vasari-auction / maisons-laffitte / art-richelieu (Drouot-Template) | HAMMER | je Sale eigener Satz, direkt von der Katalogseite gelesen ("Frais de vente : NN% TTC" -- **bereits MwSt-inklusive**, NICHT in `PREMIUM_POLICY`/`TAX_POLICY`, siehe `_load_drouot_template_json`); beobachtet 23-28 % | — | **bereits im TTC-Satz enthalten** | bestätigt (jeweilige Katalogseiten) |
| aguttes | HAMMER | gestaffelter Satz je Sale, aus `premiums` (Sale-JSON) gelesen, **HT (exkl. MwSt)** -- pro LOS gegen seinen eigenen Hammerpreis aufgelöst (Staffel kann oberhalb einer Schwelle sinken); beobachtet 21 % (Wein/Spirituosen) | — | 20 % **separat auf das Aufgeld**, NICHT im Satz enthalten -- wörtlich bestätigt in Aguttes' eigenem `terms_and_conditions`-Text (EN: "21% excl. taxes + VAT at the current rate, i.e. 25.2% incl. taxes"; FR: "20.8%HT + TVA au taux en vigueur soit 25%TTC") -- effektiver TTC-Aufschlag auf den Hammerpreis ≈ Satz × 1,20, NICHT der Satz selbst | bestätigt (Sale-JSON `terms_and_conditions`, V26VIN08) |
| astebolaffi | HAMMER | **zwei Regimes PRO LOS**, beide auf der Katalogseite selbst sichtbar/lesbar: (1) "regime del margine" (Standard, kein Symbol) -- progressiv gestaffelt 25 % bis 250k € / 22,5 % 250k-500k / 20 % 500k-1M / 18 % über 1M (für "tutte le altre aste", Wein eingeschlossen), **bereits MwSt-inklusive**; (2) "regime IVA ordinaria" (rotes Wingdings-Symbol + Tooltip am selben Los) -- FLACHER Satz, pro Los direkt aus dem Tooltip-Text gelesen (nicht hartcodiert), beobachtet 18 % | — | Regime (1): keine zusätzliche MwSt. Regime (2): MwSt zusätzlich auf Hammerpreis UND auf Aufgeld, beide Sätze ebenfalls pro Los aus dem Tooltip gelesen (beobachtet je 22 %) -- wörtlich bestätigt im Tooltip-Text ("Commissioni d'asta al 18% ... IVA sul prezzo di aggiudicazione ... tutte le altre categorie 22% ... IVA al 22% sulle commissioni") | bestätigt (Katalogseite + `/cms/termini-e-condizioni` §7/§8); Staffel-Sätze für Regime (1) sind die AKTUELLEN Terms, nicht pro Sale verifiziert -- gleicher Vorbehalt wie bei whiskyauction/langtons |

## Preis-Quelle-Invariante (D1)

- `hammer_price` = Netto-Zuschlag (OBSERVED).
- `buyer_premium` = berechnet ODER beobachtet; `price_source` markiert pro Feld
  `OBSERVED` vs. `DERIVED`.
- `realised_price` = hammer + premium (Brutto).
- `total_price` = realised + fees + tax.
- Gross-only Häuser (pandolfini, zacky, HDH-aggregate) haben **keinen** Hammer;
  `hammer_price` bleibt NULL und `realised_price` ist OBSERVED.

## MwSt-Ableitung (D3)

`tax_amount` wird nur für Häuser mit klar belegter gesetzlicher MwSt **aufs
Aufgeld** abgeleitet (`tax_amount = ROUND(buyer_premium × rate, 2)`) und auf
`total_price` aufgeschlagen:

| Haus | Rate | Land |
|---|---|---|
| winefields | 21 % | NL |
| steinfels | 8,1 % | CH |
| weinboerse | 8,1 % | CH |
| wermuth-sa | 8,1 % | CH |
| dobiaschofsky | 8,1 % auf Aufgeld | CH |
| koppe | 19 % USt | DE |
| weinauktionator | 19 % USt | DE |
| munich-wine-company | 19 % USt | DE |

Häuser mit im Aufgeld enthaltener MwSt (finarte, besch-cannes, dorotheum,
baghera) sowie nicht numerisch belegte Raten (sothebys, langtons, christies)
bleiben `tax_amount = NULL`.

aguttes steht absichtlich NICHT in dieser globalen `TAX_POLICY`-Tabelle: die
MwSt-Rate (20 %) ist pro Sale aus deren eigenem `tax_rate`-Feld gelesen (nicht
site-weit fix), daher berechnet `load_aguttes` `tax_amount` direkt inline
statt über `_apply_tax` -- gleiches Prinzip wie bei den 4 Drouot-Template-
Häusern, die ihren (dort bereits MwSt-inklusiven) Satz ebenfalls inline aus
der jeweiligen Sale anwenden.
