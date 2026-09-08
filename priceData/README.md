# Wine Price Data - Supabase Integration

Supabase-basierte Ablage für Wine-Preisdaten.

**Hinweis:** Die Python-Parser (Steinfels 315–324, Wermuth) und der Excel-Importer
sind **archiviert** → `../archive/priceData-parser/`. Die maßgebliche
Importer-Implementierung ist das Java-Modul `VinoImporter`.

## Setup

```bash
source venv/bin/activate          # oder: source .venv/bin/activate
pip install -r requirements.txt
supabase start                    # lokale Supabase-Instanz (Docker)
# .env aktualisieren (URLs/Keys aus `supabase start`)
```

## Struktur

```
priceData/
├── supabase/               # Supabase-Konfiguration + Migrationen (wine-Domain-Modell)
├── import/                 # Quell-PDFs + vorbereitete Excel-Resultate (Daten)
│   ├── steinfels/source|prepared|done
│   └── Wermuth/source|prepared|done
├── supabase_config.py      # Supabase-Client-Konfiguration
├── start_supabase.sh
└── requirements.txt
```

## Supabase Dashboard

- API: http://localhost:54321
- DB: http://localhost:54322
- Studio: http://localhost:54323

## TODO

- [ ] Entscheidung: `supabase/`-Migrations + `supabase_config.py` behalten oder ebenfalls archivieren?
- [ ] `requirements.txt` bereinigen (aktuell generisch, enthält ungenutzte Pakete).
