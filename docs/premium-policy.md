# Premium-/Gebühren-Policy je Haus (Ground Truth)

Stand: 2026-10-13. Dies ist die verbindliche Gebührenstruktur je Haus, aus
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
| koppe | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| weinauktionator | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| dobiaschofsky | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| wermuth-sa | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| besch-cannes | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| munich-wine-company | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| winebarrel | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |

## Preis-Quelle-Invariante (D1)

- `hammer_price` = Netto-Zuschlag (OBSERVED).
- `buyer_premium` = berechnet ODER beobachtet; `price_source` markiert pro Feld
  `OBSERVED` vs. `DERIVED`.
- `realised_price` = hammer + premium (Brutto).
- `total_price` = realised + fees + tax.
- Gross-only Häuser (pandolfini, zacky, HDH-aggregate) haben **keinen** Hammer;
  `hammer_price` bleibt NULL und `realised_price` ist OBSERVED.
