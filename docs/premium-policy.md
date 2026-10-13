# Premium-/Gebühren-Policy je Haus (Ground Truth)

Stand: 2026-10-13. Dies ist die verbindliche Gebührenstruktur je Haus, aus
Primärquellen (Terms/Conditions) zu pflegen. Spalten: Preis-Basis (was der
Fetcher liefert), Buyer's Premium, Fees (Lotgebühr), MwSt/VAT, Quelle.

| Haus | Preis-Basis | Buyer's Premium | Fees | MwSt | Quelle/Status |
|---|---|---|---|---|---|
| sothebys | HAMMER | gestaffelt 26 %/21 %/14,5 % + Overhead 1 % | — | VAT on premium | bestätigt (Terms) |
| pandolfini | HAMMER_PLUS_BUYERS_PREMIUM | im Preis enthalten | — | — | bestätigt |
| zacky | HAMMER_PLUS_BUYERS_PREMIUM | im Preis enthalten | — | — | bestätigt |
| hdh | HAMMER (`hammer`), `aggregate` inkl. Premium | `aggregate - hammer` | — | — | bestätigt |
| idealwine | (cote, kein Hammer) | 25,2 % TTC bis 26.03.2026, 25,8 % TTC ab 01.04.2026 | — | inkl. TTC | bestätigt |
| weinauktionator | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| steinfels | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| weinboerse | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| baghera | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| dobiaschofsky | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| wermuth-sa | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| koppe | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| finarte | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| dorotheum | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| besch-cannes | HAMMER | **offen** | **offen** | **offen** | zu ermitteln |
| langtons | HAMMER (`winning_bid`) | **offen** | **offen** | **offen** | zu ermitteln |
| winefields | HAMMER (`hammer`) | **offen** | **offen** | **offen** | zu ermitteln |
| christies | HAMMER | **offen** (gestaffelt je Standort) | **offen** | **offen** | zu ermitteln |
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
