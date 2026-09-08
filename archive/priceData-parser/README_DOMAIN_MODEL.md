# Wine Price Data Analysis Project

Dieses Projekt implementiert ein vollständiges Wine Price Data System basierend auf dem ursprünglichen Hibernate Domain Model von 2010, portiert zu Supabase/PostgreSQL.

## Domain Model

Das System basiert auf den ursprünglichen Hibernate Mapping Files (HBM) und implementiert folgende Entitäten:

### Core Entities

#### Wine (Wein)
- **id**: Eindeutige ID (Sequence-basiert)
- **name**: Name des Weins
- **producer**: Produzent/Weingut  
- **vintage**: Jahrgang
- **region**: Weinregion (z.B. Pomerol, Margaux)
- **origin**: Herkunftsland/Gebiet (z.B. Bordeaux, France)

#### Rating (Bewertung)
- **id**: Eindeutige ID
- **wine_id**: Referenz zum bewerteten Wein
- **agency_id**: Referenz zur Bewertungsagentur
- **score**: Punktzahl/Bewertung

#### RatingAgency (Bewertungsagentur)
- **id**: Eindeutige ID
- **ratingagencyname**: Name der Agentur (z.B. "Robert Parker / Wine Advocate")
- **maxpoints**: Maximale Punktzahl (z.B. 100, 20)

#### Provider (Anbieter/Auktionshaus)
- **id**: Eindeutige ID
- **name**: Name des Anbieters (z.B. "Sotheby's Wine Auctions")

#### Offering (Preisangebot/Auktion)
- **id**: Eindeutige ID
- **provider_id**: Referenz zum Anbieter
- **pricemin**: Mindestpreis
- **pricemax**: Höchstpreis  
- **offeringdate**: Angebotsdatum
- **providerofferingid**: Externe Angebots-ID beim Anbieter
- **realizedprice**: Realisierter Verkaufspreis
- **isohk**: Flag für Hong Kong Offerings
- **eventidentifier**: Auktions-/Event-Bezeichnung
- **note**: Notizen/Zusatzinformationen

#### Unit (Einheit/Flaschengröße)
- **id**: Eindeutige ID
- **deciliters**: Größe in Dezilitern (z.B. 7.5 für 750ml Standardflasche)

#### WineOffering (Wein-Angebots-Verknüpfung)
- **id**: Eindeutige ID
- **wine_id**: Referenz zum Wein
- **offering_id**: Referenz zum Angebot
- **wineunit_id**: Referenz zur Flaschengröße

## Quick Start

### 1. Python Environment Setup
```bash
# Virtual environment aktivieren
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt
```

### 2. Supabase Local Development
```bash
# Supabase starten
./start_supabase.sh

# Oder manuell:
supabase start
```

### 3. Test the Domain Model
```bash
# Complete domain test ausführen
python test_wine_domain.py
```

## Database Schema

### Vorpopulierte Daten

#### Rating Agencies
- Robert Parker / Wine Advocate (100 Punkte)
- Wine Spectator (100 Punkte)  
- James Suckling (100 Punkte)
- Jancis Robinson (20 Punkte)
- Antonio Galloni / Vinous (100 Punkte)
- Decanter (5 Punkte)
- Falstaff (100 Punkte)
- Vinum (20 Punkte)
- Wine Enthusiast (100 Punkte)
- Bettane & Desseauve (20 Punkte)

#### Standard Wine Units
- 3.75cl (Half bottle)
- 7.5cl (Standard bottle)  
- 15.0cl (Magnum)
- 30.0cl (Double Magnum)
- 45.0cl (Jeroboam)
- 60.0cl (Imperial)
- 90.0cl (Salmanazar)
- 120.0cl (Balthazar)
- 150.0cl (Nebuchadnezzar)
- 180.0cl (Melchior)

## Usage Examples

### Basic Wine Operations
```python
from supabase_config import SupabaseConfig

config = SupabaseConfig()
client = config.get_client()

# Add a wine
wine = client.table('wine').insert({
    'name': 'Château Pétrus',
    'producer': 'Château Pétrus', 
    'vintage': 2005,
    'region': 'Pomerol',
    'origin': 'Bordeaux, France'
}).execute()

# Search wines by region
pomerol_wines = client.table('wine').select('*').eq('region', 'Pomerol').execute()

# Search wines by vintage
vintage_2005 = client.table('wine').select('*').eq('vintage', 2005).execute()
```

### Adding Ratings
```python
# Add a Robert Parker rating
parker_agency = client.table('ratingagency').select('*').eq('ratingagencyname', 'Robert Parker / Wine Advocate').execute()

rating = client.table('rating').insert({
    'wine_id': wine_id,
    'agency_id': parker_agency.data[0]['id'],
    'score': 96.0
}).execute()
```

### Market Data / Offerings
```python
# Add auction house
provider = client.table('provider').insert({
    'name': "Sotheby's Wine Auctions"
}).execute()

# Add auction offering
offering = client.table('offering').insert({
    'provider_id': provider_id,
    'pricemin': 2500.0,
    'pricemax': 3500.0,
    'offeringdate': '2024-01-15',
    'realizedprice': 3200.0,
    'eventidentifier': 'Fine & Rare Wines Auction January 2024'
}).execute()

# Link wine to offering with bottle size
wine_offering = client.table('wineoffering').insert({
    'wine_id': wine_id,
    'offering_id': offering_id,
    'wineunit_id': standard_bottle_id  # 7.5cl
}).execute()
```

### Complex Queries
```python
# Get wine with all ratings and market data
wine_complete = client.table('wineoffering').select('''
    wine:wine_id (
        name, producer, vintage, region, origin
    ),
    unit:wineunit_id (
        deciliters
    ),
    offering:offering_id (
        pricemin, pricemax, realizedprice, offeringdate,
        provider:provider_id (
            name
        )
    )
''').eq('wine_id', wine_id).execute()

# Get all ratings for a wine
ratings = client.table('rating').select('''
    score,
    ratingagency:agency_id (
        ratingagencyname, maxpoints
    )
''').eq('wine_id', wine_id).execute()
```

## Architecture

### Migration Files
- `20250801000001_create_wine_tables.sql`: Initial simple schema (ersetzt)
- `20250801000002_create_wine_domain_model.sql`: Complete Hibernate-based domain model

### Python Modules
- `supabase_config.py`: Supabase client configuration
- `test_wine_domain.py`: Comprehensive domain model test
- `wine_domain_manager.py`: Manager class (in development)
- `requirements.txt`: Python dependencies

### Supabase Services
- **Database**: PostgreSQL 17 (localhost:54322)
- **API**: Supabase API (localhost:54321)  
- **Studio**: Web interface (localhost:54323)
- **Auth**: Authentication service
- **Storage**: File storage service

## Legacy Integration

Dieses System konvertiert die ursprünglichen Hibernate XML Mappings von 2010:
- `Wine.hbm.xml` → `wine` table
- `Rating.hbm.xml` → `rating` table  
- `RatingAgency.hbm.xml` → `ratingagency` table
- `Offering.hbm.xml` → `offering` table
- `Provider.hbm.xml` → `provider` table
- `WineOffering.hbm.xml` → `wineoffering` table
- `Unit.hbm.xml` → `unit` table

Alle Original-Hibernate-Sequenzen werden als PostgreSQL-Sequenzen implementiert.

## Features

- ✅ **Complete Domain Model**: Alle Entitäten aus den HBM Files portiert
- ✅ **Relationships**: Foreign Keys und Referential Integrity  
- ✅ **Search & Queries**: Flexible Suche nach verschiedenen Kriterien
- ✅ **Market Data**: Vollständige Preis- und Auktionsdaten
- ✅ **Rating System**: Multi-Agency Bewertungssystem
- ✅ **Unit Management**: Verschiedene Flaschengrößen
- ✅ **Provenance Tracking**: Herkunft und Auktionshistorie
- ✅ **Real-time API**: Supabase Real-time subscriptions möglich
- ✅ **Row Level Security**: Supabase RLS policies implementiert

## Development

```bash
# Database reset with new migrations
supabase db reset

# Check migration status  
supabase db status

# View logs
supabase logs

# Access Supabase Studio
open http://localhost:54323
```

## Environment Variables

Required in `.env`:
```
SUPABASE_URL=http://127.0.0.1:54321
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Diese werden automatisch von `supabase start` generiert.

---

**Migration von Hibernate zu Supabase erfolgreich abgeschlossen!** 🍷  
Das ursprüngliche Domain Model von 2010 ist vollständig in modernem PostgreSQL/Supabase implementiert.
