# Steinfels Wine Price Data Parser

## Projekt Struktur

```
src/
├── utils/
│   └── wine_unit_detector.py          # Intelligente Erkennung von Weineinheiten (global)
├── steinfels/
│   ├── wine_unit_detector.py          # Steinfels-spezifische Utility
│   └── 2002/
│       └── 315/
│           ├── parser_315.py          # Enhanced Parser für 315.pdf (ERFOLGREICHE IMPLEMENTIERUNG)
│           └── results_315.xlsx       # Parsed Resultate (560 Weine, bereit für Review)
└── README.md

archive/                                # Alte Entwicklungsversionen
├── steinfels_final_parser.py          # Vorherige Iteration
├── steinfels_robust_parser.py         # Vorherige Iteration  
├── steinfels_pdf_to_excel.py          # Experimenteller Ansatz
├── test_parsing_patterns.py           # Test-Utilities
└── analyze_315_pdf.py                 # PDF-Analyse Tool
```

## Parser Status

### ✅ Erfolgreich implementiert
- **315.pdf**: 560 Weine erfolgreich geparst
  - 34 einzigartige Regionen erkannt
  - 31 Weine mit Produzenten
  - CHF 377.87 durchschnittlicher Preis
  - Intelligente Einheitenerkennung (7.5dl, 15.0dl, 30.0dl)
  - Text-Bereinigung (1er, 2ème, Klammern entfernt)

### 🔄 Ausstehend
- **316.pdf**: Parser noch zu entwickeln
- **317.pdf**: Parser noch zu entwickeln 
- **318.pdf**: Parser noch zu entwickeln
- **319.pdf**: Parser noch zu entwickeln

## Verwendung

1. **Enhanced Parser (315.pdf)**:
   ```python
   python src/steinfels/2002/315/parser_315.py
   ```

2. **Wine Unit Detector**:
   ```python
   from src.utils.wine_unit_detector import detect_wine_unit
   unit, quantity, is_ohk = detect_wine_unit("6 Flaschen 0.75l")
   ```

## Nächste Schritte

1. Manuelle Überprüfung von `results_315.xlsx`
2. Parser für 316.pdf entwickeln (wahrscheinlich Anpassungen nötig)
3. Fortsetzung mit 317.pdf, 318.pdf, 319.pdf
4. Excel-to-Database Import implementieren
