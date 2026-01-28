# Wine Price Data - Supabase Integration

Dieses Projekt nutzt Supabase als lokale Datenbank für Wine-Preisdaten.

## 🚀 Setup

### 1. Virtuelle Umgebung aktivieren
```bash
source venv/bin/activate
```

### 2. Dependencies installieren
```bash
pip install -r requirements.txt
```

### 3. Lokale Supabase-Entwicklungsumgebung starten
```bash
supabase start
```

### 4. Environment-Variablen konfigurieren
Nach dem Start von Supabase werden die korrekten URLs und API-Keys ausgegeben. Aktualisieren Sie die `.env` Datei entsprechend.

## 📁 Projektstruktur

```
priceData/
├── venv/                     # Python virtual environment
├── supabase/                 # Supabase Konfiguration
│   ├── config.toml          # Lokale Supabase-Einstellungen
│   └── migrations/          # Datenbank-Migrationen
│       └── 20250801000001_create_wine_tables.sql
├── .env                     # Environment-Variablen
├── requirements.txt         # Python Dependencies
├── supabase_config.py       # Supabase Client-Konfiguration
├── wine_manager.py          # Wine-Daten Management
└── README.md                # Diese Datei
```

## 🗄️ Datenbank Schema

### Tabellen:
- **wines**: Haupttabelle für Weindaten
- **wine_prices**: Preishistorie
- **wine_reviews**: Bewertungen

### Wine-Tabelle Features:
- Vollständige Weininformationen (Name, Produzent, Jahrgang, Region)
- Preise und Bewertungen
- Tasting Notes (JSON)
- Food Pairing Empfehlungen
- Verfügbarkeitsstatus

## 🐍 Python API

### Beispiel Verwendung:

```python
from wine_manager import WineManager

# Wine Manager initialisieren
wine_manager = WineManager()

# Wein hinzufügen
wine_data = {
    "name": "Château Margaux 2010",
    "producer": "Château Margaux",
    "vintage": 2010,
    "region": "Margaux",
    "country": "France",
    "wine_type": "red",
    "price": 450.00,
    "rating": 98.0
}
wine = wine_manager.add_wine(wine_data)

# Weine suchen
results = wine_manager.search_wines("Château")

# Preishistorie hinzufügen
wine_manager.add_price_history(wine['id'], {
    "price": 445.00,
    "retailer": "Wine Shop",
    "currency": "EUR"
})
```

## 🌐 Supabase Dashboard

Nach dem Start ist das lokale Supabase Dashboard erreichbar unter:
- **API**: http://localhost:54321
- **DB**: http://localhost:54322
- **Studio**: http://localhost:54323

## 📊 Beispieldaten

Das Projekt enthält Beispieldaten für:
- Château Margaux 2010 (Bordeaux)
- Dom Pérignon 2012 (Champagne)
- Barolo Brunate 2018 (Piemont)

Führen Sie das Wine Manager Skript aus, um die Beispieldaten zu laden:
```bash
python wine_manager.py
```

## 🛠️ Entwicklung

### Neue Migration erstellen:
```bash
supabase migration new migration_name
```

### Migration anwenden:
```bash
supabase db reset
```

### Supabase stoppen:
```bash
supabase stop
```

## 🔧 Troubleshooting

1. **Docker nicht gefunden**: Stellen Sie sicher, dass Docker Desktop läuft
2. **Port-Konflikte**: Ports 54321-54323 müssen frei sein
3. **Environment-Variablen**: Überprüfen Sie die `.env` Datei nach dem ersten Start

## 📝 TODO

- [ ] Data Import Scripts für verschiedene Wine APIs
- [ ] Automatische Preisüberwachung
- [ ] Wine Recommendation Engine
- [ ] Export-Funktionen
- [ ] Web Dashboard mit Streamlit
