# Forecast Calibration Report

Stand: 2026-11-20 -- Stufe 4.1 (Split-Conformal, local_level), Stufe 3 als Regel (3.6) statt Modell. Details/Begruendung: data/forecast/calibrate.py Modul-Docstring.

## Horizon: next

FIT-Origins: ['2025-01-01', '2025-07-01', '2026-01-01'] -- TEST-Origin (held-out): 2026-07-01

gap_days (Tage Origin->realisierte Zielzeile) -- FIT: median=121 p90=381 (n=67860); TEST: median=61 p90=103 (n=6777) -- siehe Modul-Docstring Punkt 2 (Rechtszensierung des TEST-Origins, bewusst nicht korrigiert).

| density_class | n (test) | Coverage 50% | Coverage 80% | Coverage 95% | Entscheidung |
|---|---|---|---|---|---|
| 1-2 | 288 | 0.642 | 0.872 | 0.972 | INSUFFICIENT_DATA |
| 10+ | 5110 | 0.555 | 0.832 | 0.958 | INSUFFICIENT_DATA |
| 3-4 | 502 | 0.610 | 0.855 | 0.964 | INSUFFICIENT_DATA |
| 5-9 | 877 | 0.633 | 0.869 | 0.969 | INSUFFICIENT_DATA |

## Horizon: 12m

FIT-Origins: ['2025-01-01'] -- TEST-Origin (held-out): 2025-07-01

gap_days (Tage Origin->realisierte Zielzeile) -- FIT: median=176 p90=334 (n=81838); TEST: median=274 p90=342 (n=48074) -- siehe Modul-Docstring Punkt 2 (Rechtszensierung des TEST-Origins, bewusst nicht korrigiert).

| density_class | n (test) | Coverage 50% | Coverage 80% | Coverage 95% | Entscheidung |
|---|---|---|---|---|---|
| 1-2 | 2562 | 0.545 | 0.824 | 0.950 | forecast |
| 10+ | 36153 | 0.516 | 0.800 | 0.949 | forecast |
| 3-4 | 3582 | 0.527 | 0.812 | 0.963 | forecast |
| 5-9 | 5777 | 0.542 | 0.820 | 0.963 | forecast |

