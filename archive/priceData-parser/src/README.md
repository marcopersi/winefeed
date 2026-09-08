# Steinfels Wine Price Data Parser

Python-Parser für Steinfels-PDFs. **Hinweis:** redundant zum Java-Modul
`VinoImporter` (siehe `CLEANUP_PLAN.md`), das für den Steinfels-/Wermuth-Import
maßgeblich ist.

## Struktur

```
src/
├── utils/
│   └── wine_unit_detector.py          # Einheitenerkennung (dl, OHK)
├── steinfels/
│   ├── base_parser.py                 # Template-Method-Basisklasse
│   ├── 2002/315..319/                 # parser_*.py
│   └── 2003/320..324/                 # parser_*.py
└── README.md

../archive/                            # alte Parser-Iterationen
```

## Verwendung

```bash
python src/steinfels/2002/315/parser_315.py
```

## Einheitenerkennung

```python
from src.utils.wine_unit_detector import WineUnitDetector
detector = WineUnitDetector()
quantity, deciliters, description, is_ohk = detector.parse_wine_quantity_and_unit("6 Magnum")
```
