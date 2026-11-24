# Bauplan: Lot-Normalisierung (LLM, batched, alle Lots)

> **⚠ Abgelöst durch `.opencode/plans/wine-pipeline-v2.md` (§4).** Der
> Alle-Lots-LLM-Ansatz (2,77 Mio Lots, ~$150–250) entfällt: Der LLM läuft
> **offline auf distinkten Aliassen** (≈10× weniger), **nie im Build**, und
> nur als Residuum nach den lokalen Stufen 0–2. Dieser Plan bleibt nur als
> Historie stehen.

## 1. Summary

- **Ziel:** Jeden Lot per LLM in eine strukturierte Form normalisieren —
  `jahrgang` (zwingend), `produzent`, `wein`, `gebinde/unit`, `anzahl`,
  `herkunft`, `is_ohk`, `price_per_bottle` — statt des rohen Beschreibungstexts.
- **Betroffen:** Normalisierung (LLM-Offline-Tool), Schema (`lots`), Rebuild.
- **Hauptrisiko:** Kosten + Laufzeit (2,77 Mio Lots), falsche Extraktion.
- **Business-Logik betroffen:** ja (Wein-/Lot-Identität).

## 2. Established facts

- 1.313.257 Lots (47 %) ohne `vintage`; 66.487 `MIXED`; `quantity` bei 70 %.
- `_separate_vintage` zieht den Jahrgang nur aus trivialen Fällen; Mixed-Lots
  (Vertikalen, „(2 BT)") bleiben roh.
- Petrus-Beispiele zeigen: Jahrgang, Produzent, Gebinde, Anzahl und Herkunft
  sind vermischt im Text; „(2 BT)" = 2 Flaschen, „Vertical" = mehrere Jahrgänge.

## 3. Scope

- **In scope:** LLM-Normalisierung aller 2,77 Mio Lots (strukturierte Felder),
  Schema-Erweiterung, `price_per_bottle` (= `total_price`/`quantity`, nur wenn
  ein Wein/Jahrgang), `is_ohk` (ohk/cbo/owc im Text), Rebuild.
- **Out of scope:** GUI-UX, der volle FX-Verlauf (separates Projekt — braucht
  eine FX-Quelle für historische Kurse).
- **Unresolved:** LLM-Schema (Feldliste), Batch-Grösse, Kostenbudget.

## 4. Evolutionary micro-steps

- **Step 1 — LLM-Schema + Prompt:** Feldliste festlegen (jahrgang, produzent,
  wein, gebinde/unit, anzahl, herkunft, is_ohk) + System-Prompt („Jahrgang ist
  eine 4-stellige Jahreszahl; Vertical = mehrere Jahrgänge → Liste; ohne
  erkennbaren Jahrgang → null"). Validierung: Prompt an den Petrus/Sassicaia/
  Bernhard-Huber-Beispielen testen. Completion: Schema + Prompt freigegeben.
- **Step 2 — Batch-Skript:** `data/llm_normalize_lots.py` (Offline, resumable,
  non-thinking, 429-Retry, inkrementelles Schreiben, Kosten-Tracking) —
  Eingabe `raw_wine` + `description` + Auktionsinfo, Ausgabe strukturierte CSV.
  Validierung: Stichprobe + Kosten-Schätzung. Completion: Skript läuft, Kosten klar.
- **Step 3 — Schema-Update:** `lots` um die Felder erweitern (z. B. `gebinde`,
  `anzahl`, `herkunft`, `is_ohk`, `price_per_bottle`) + Loader-Anpassung.
  Validierung: `PRAGMA table_info`, Unit-Tests. Completion: Schema migriert.
- **Step 4 — Rebuild + Validierung:** Master-DB neu bauen (mit den LLM-Feldern),
  Stichproben (Petrus/Sassicaia/Huber), Idempotenz-Check. Completion: Zahlen grün.

## 5. Validation matrix

| Betroffenes | Validierung |
|---|---|
| Prompt/Schema | Beispiel-Stichprobe (Petrus/Sassicaia/Huber) |
| Batch-Skript | Unit-Test + Kosten-Schätzung + Resume-Test |
| Schema | `PRAGMA table_info`, Loader-Unit-Tests |
| Rebuild | `vintage`-Abdeckung steigt, `is_ohk`/`price_per_bottle` gefüllt |
| Gesamt | `python -m unittest discover -s data/tests` |

## 6. Risks and rollback

- **Kosten:** 2,77 Mio Lots × ~150–250 Tokens ≈ $150–250 (non-thinking Flash).
  Rollback: nur einen Teil normalisieren, Budget-Limit im Skript.
- **Falsche Extraktion:** LLM nur als Offline-Tool; Ergebnis als kuratierte
  Felder, Build bleibt deterministisch.
- **Rebuild:** atomar (tmp + `os.replace`), Backup `.bak-*`.

## 7. Approval gate

Freigabe für Step 1 (Schema + Prompt) und die Kosten-/Batch-Entscheidung.
Der volle FX-Verlauf wird als separates Issue geführt.

## Progress

- [ ] Step 1: LLM-Schema + Prompt
- [ ] Step 2: Batch-Skript
- [ ] Step 3: Schema-Update
- [ ] Step 4: Rebuild + Validierung
