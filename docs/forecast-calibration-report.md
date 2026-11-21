# Forecast Calibration Report

Stand: 2026-11-20 -- Stufe 4.1 (Split-Conformal, local_level), Stufe 3 als Regel (3.6) statt Modell. Details/Begruendung: data/forecast/calibrate.py Modul-Docstring.

## Horizon: next

FIT-Origins: ['2025-01-01', '2025-07-01', '2026-01-01'] -- TEST-Origin (held-out): 2026-07-01

gap_days (Tage Origin->realisierte Zielzeile) -- FIT: median=106 p90=332 (n=60883); TEST: median=68 p90=103 (n=10084) -- siehe Modul-Docstring Punkt 2 (Rechtszensierung des TEST-Origins, bewusst nicht korrigiert).

| density_class | n (test) | Coverage 50% | Coverage 80% | Coverage 95% | Entscheidung |
|---|---|---|---|---|---|
| 1-2 | 732 | 0.556 | 0.861 | 0.973 | INSUFFICIENT_DATA |
| 10+ | 6464 | 0.547 | 0.827 | 0.958 | forecast |
| 3-4 | 1132 | 0.568 | 0.836 | 0.959 | INSUFFICIENT_DATA |
| 5-9 | 1756 | 0.579 | 0.838 | 0.966 | INSUFFICIENT_DATA |

## Horizon: 12m

FIT-Origins: ['2025-01-01'] -- TEST-Origin (held-out): 2025-07-01

gap_days (Tage Origin->realisierte Zielzeile) -- FIT: median=99 p90=165 (n=41860); TEST: median=202 p90=335 (n=86956) -- siehe Modul-Docstring Punkt 2 (Rechtszensierung des TEST-Origins, bewusst nicht korrigiert).

| density_class | n (test) | Coverage 50% | Coverage 80% | Coverage 95% | Entscheidung |
|---|---|---|---|---|---|
| 1-2 | 3601 | 0.474 | 0.773 | 0.921 | forecast |
| 10+ | 67541 | 0.503 | 0.803 | 0.955 | forecast |
| 3-4 | 5868 | 0.484 | 0.792 | 0.957 | forecast |
| 5-9 | 9946 | 0.502 | 0.803 | 0.964 | forecast |

