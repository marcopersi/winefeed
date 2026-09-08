#!/usr/bin/env python3
"""
Direct Parser for 317.pdf structured data
Simple conversion from structured text to enhanced format with all wines
"""

import pandas as pd
import re
import os
import sys

# Add the parent directories to path to import utilities
sys.path.append('/Users/marcopersi/development/winefeed/priceData/src/utils')

try:
    from wine_unit_detector import convert_unit_to_deciliters
except ImportError:
    print("Warning: Could not import wine_unit_detector. Using fallback.")
    def convert_unit_to_deciliters(quantity_text):
        """Fallback unit conversion"""
        if "Magnum" in quantity_text:
            return 15.0
        elif "3/8" in quantity_text:
            return 2.8125
        else:
            return 7.5


def clean_wine_name(name):
    """Clean OCR errors in wine names"""
    fixes = [
        # OCR corrections
        ('ChGteau', 'Chateau'),
        ('Chdteau', 'Chateau'),
        ('Ch&teau', 'Chateau'),
        ('Chéteau', 'Chateau'),
        ('Ch@teau', 'Chateau'),
        ('ChdGteau', 'Chateau'),
        ('Chd&teau', 'Chateau'),
        ('Ch4teau', 'Chateau'),
        ('ChG&teau', 'Chateau'),
        ('Chteau', 'Chateau'),
        ('Cha&teau', 'Chateau'),
        # Classification fixes
        ('ler Cru', '1er Cru'),
        ('@me', 'ème'),
        ('4me', 'ème'),
        ('2me', 'ème'),
        ('6me', 'ème'),
        ('5me', 'ème'),
        ('3me', 'ème'),
        ('eme', 'ème'),
        ('26me', '2ème'),
        ('22me', '2ème'),
        ('€me', 'ème'),
        # Region fixes
        ('Saint-Emi', 'Saint-Emilion'),
        ('Sai', 'Saint-Julien'),
        ('Pa', 'Pauillac'),
        ('Pauillacpe', 'Pape'),
        ('Pauillacscal', 'Pascal'),
        ('Pauillacolo', 'Paolo'),
        ('Pauillacternina', 'Paternina'),
        ('Pauillaclacios', 'Palacios'),
        ('Pauillachimeyer', 'Pahlmeyer'),
        ('Pauillacvillon', 'Pavillon'),
        ('Pauillacnsi', 'Pansi'),
        ('Saint-Juliennt', 'Saint'),
        ('Saint-Juliennt-', 'Saint-'),
        ('Saint-Emilionlion', 'Saint-Emilion'),
        # Wine name fixes
        ('Chdateauneuf-du-', 'Chateauneuf-du-'),
        ('Chateauneuf-du-Pauillacpe', 'Chateauneuf-du-Pape'),
        ('Ormellaia', 'Ornellaia'),
        ('Don Pauillacscal', 'Don Pascal'),
    ]
    
    for old, new in fixes:
        name = name.replace(old, new)
    
    return name.strip()


def extract_region(wine_name):
    """Extract wine region from name"""
    regions = [
        'Saint-Emilion', 'Saint-Julien', 'Pauillac', 'Margaux', 'Pomerol',
        'Haut-Médoc', 'Médoc', 'Pessac-Léognan', 'Graves', 'Sauternes',
        'Saint-Estéphe', 'Moulis', 'Listrac', 'Bordeaux', 'Haut-Médoc',
        'Bourgogne', 'Burgundy', 'Côte de Nuits', 'Côte de Beaune',
        'Champagne', 'Rhône', 'Châteauneuf-du-Pape', 'Hermitage',
        'Crozes-Hermitage', 'Barolo', 'Barbaresco', 'Brunello di Montalcino',
        'Chianti', 'Toscana', 'Tuscany', 'Piemont', 'Rioja', 'Ribera del Duero',
        'Priorat', 'Navarra', 'California', 'Napa Valley', 'Sonoma',
        'Bordeaux Supérieur'
    ]
    
    wine_upper = wine_name.upper()
    
    for region in regions:
        if region.upper() in wine_upper:
            return region
    
    # Check for abbreviated regions in wine names
    if 'PAUILLAC' in wine_upper or 'PAULL' in wine_upper:
        return 'Pauillac'
    elif 'SAINT-JULIEN' in wine_upper or 'ST-JULIEN' in wine_upper:
        return 'Saint-Julien'
    elif 'SAINT-EMILION' in wine_upper or 'ST-EMILION' in wine_upper:
        return 'Saint-Emilion'
    elif 'MARGAUX' in wine_upper:
        return 'Margaux'
    elif 'POMEROL' in wine_upper:
        return 'Pomerol'
    elif 'SAINT-ESTEPHE' in wine_upper or 'SAINT-ESTÈPHE' in wine_upper:
        return 'Saint-Estéphe'
    elif 'PESSAC' in wine_upper:
        return 'Pessac-Léognan'
    elif 'GRAVES' in wine_upper:
        return 'Graves'
    elif 'SAUTERNES' in wine_upper:
        return 'Sauternes'
    elif 'BARBARESCO' in wine_upper:
        return 'Barbaresco'
    elif 'BAROLO' in wine_upper:
        return 'Barolo'
    elif 'BRUNELLO' in wine_upper:
        return 'Brunello di Montalcino'
    elif 'RIOJA' in wine_upper:
        return 'Rioja'
    elif 'CHATEAUNEUF' in wine_upper or 'CHÂTEAUNEUF' in wine_upper:
        return 'Châteauneuf-du-Pape'
    elif any(name in wine_upper for name in ['CHAMBERTIN', 'GEVREY', 'MOREY', 'CLOS DE VOUGEOT', 'MUSIGNY', 'ROMANÉE', 'VOSNE', 'NUITS', 'POMMARD', 'VOLNAY', 'BEAUNE', 'MEURSAULT', 'CORTON', 'CHABLIS']):
        return 'Burgundy'
    elif 'CHAMPAGNE' in wine_upper:
        return 'Champagne'
    
    return 'Unknown'


def extract_classification(wine_name):
    """Extract wine classification"""
    classifications = [
        '1er Cru A', '1er Cru B', '1er Cru', 'Grand Cru', 
        '2ème Cru', '3ème Cru', '4ème Cru', '5ème Cru',
        'Cru Bourgeois', 'Cru Beaujolais', 'Riserva'
    ]
    
    for classification in classifications:
        if classification in wine_name:
            return classification
    
    return ''


def parse_structured_wines():
    """Parse all wines from structured file"""
    
    input_file = 'wines_final.txt'
    
    try:
        with open(input_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()
    except FileNotFoundError:
        print(f"Error: Could not find {input_file}")
        return pd.DataFrame()
    
    wines = []
    
    # Skip header line
    for line in lines[1:]:
        if not line.strip():
            continue
        
        parts = line.strip().split('\t')
        if len(parts) < 3:  # Need at least lot, product, quantity
            continue
        
        lot_number = parts[0]
        product_name = parts[1]
        quantity_text = parts[2]
        vintage = parts[3] if len(parts) > 3 and parts[3] else ""
        price_text = parts[4] if len(parts) > 4 and parts[4] else ""
        
        # Skip invalid entries
        if not product_name or product_name == "Flaschen +":
            continue
        
        try:
            lot_num = int(lot_number)
        except ValueError:
            continue
        
        # Clean wine name
        cleaned_name = clean_wine_name(product_name)
        
        # Extract components
        region = extract_region(cleaned_name)
        classification = extract_classification(cleaned_name)
        
        # Parse price - be more careful with year vs price
        price_chf = 0.0
        if price_text:
            # If it looks like a year (1900-2099), it's not a price
            if price_text.isdigit() and 1900 <= int(price_text) <= 2099:
                price_chf = 0.0
            else:
                try:
                    price_chf = float(price_text.replace("'", ""))
                except ValueError:
                    price_chf = 0.0
        
        # Convert units
        unit_dl = convert_unit_to_deciliters(quantity_text)
        
        # Extract producer (simple approach)
        producer = ""
        if "Antinori" in cleaned_name:
            producer = "Antinori"
        elif "Tenuta dell'Ornellaia" in cleaned_name:
            producer = "Tenuta dell'Ornellaia"
        elif "Tenuta San Guido" in cleaned_name:
            producer = "Tenuta San Guido"
        elif "Domaine" in cleaned_name:
            producer_match = re.search(r'Domaine ([^,\s]+(?:\s+[^,\s]+)*)', cleaned_name)
            if producer_match:
                producer = f"Domaine {producer_match.group(1).strip()}"
        
        # Check for OHK
        ohk = "Yes" if "OHK" in quantity_text else "No"
        
        wine_entry = {
            'Lot': lot_num,
            'Wine': cleaned_name,
            'Region': region,
            'Classification': classification,
            'Producer': producer,
            'Year': vintage,
            'Unit': unit_dl,
            'Quantity_Text': quantity_text,
            'Price_CHF': price_chf,
            'Price_Text': price_text,
            'OHK': ohk
        }
        
        wines.append(wine_entry)
    
    df = pd.DataFrame(wines)
    print(f"Successfully parsed {len(wines)} wines from structured file")
    return df


def main():
    """Convert structured data to enhanced format"""
    
    print("=== Direct Parser for 317 structured data ===")
    
    df = parse_structured_wines()
    
    if df.empty:
        print("No wines parsed")
        return
    
    # Save to Excel
    output_file = "results_317_direct.xlsx"
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Wines', index=False)
        
        # Statistics
        stats_data = {
            'Metric': ['Total Wines', 'Unique Regions', 'With Prices', 'With Vintage', 'Average Price'],
            'Value': [
                len(df),
                len(df['Region'].unique()),
                len(df[df['Price_CHF'] > 0]),
                len(df[df['Year'] != '']),
                f"CHF {df[df['Price_CHF'] > 0]['Price_CHF'].mean():.2f}" if len(df[df['Price_CHF'] > 0]) > 0 else "N/A"
            ]
        }
        
        stats_df = pd.DataFrame(stats_data)
        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
    
    print(f"\n🎉 SUCCESS! Parsed {len(df)} wines")
    print(f"📁 Saved to: {output_file}")
    
    # Show sample results
    print(f"\nFirst 15 wines:")
    for i, row in df.head(15).iterrows():
        price_str = f"CHF {row['Price_CHF']}" if row['Price_CHF'] > 0 else "No price"
        print(f"  {row['Lot']:3d}. {row['Wine'][:50]:50s} | {row['Region']:15s} | {row['Year']:4s} | {price_str:10s}")
    
    # Statistics
    regions_with_data = df[df['Region'] != 'Unknown']['Region'].value_counts()
    print(f"\nTop regions:")
    for region, count in regions_with_data.head(10).items():
        print(f"  {region}: {count} wines")
    
    print(f"\nData completeness:")
    print(f"  Wines with region identified: {len(df[df['Region'] != 'Unknown'])}/{len(df)} ({100*len(df[df['Region'] != 'Unknown'])/len(df):.1f}%)")
    print(f"  Wines with vintage: {len(df[df['Year'] != ''])}/{len(df)} ({100*len(df[df['Year'] != ''])/len(df):.1f}%)")
    print(f"  Wines with price: {len(df[df['Price_CHF'] > 0])}/{len(df)} ({100*len(df[df['Price_CHF'] > 0])/len(df):.1f}%)")


if __name__ == "__main__":
    main()
