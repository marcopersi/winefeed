#!/usr/bin/env python3
"""
Test specific wine lines to fix parsing patterns
"""

import re

def test_parsing_patterns():
    """Test specific problematic lines"""
    
    test_lines = [
        "1 Château Le Fournas Bernadotte Haut-Médoc 12 Flaschen OHK 1976 210",
        "391 Château Lafite Rothschild Pauillac 1er 1 Magnum 1986 700",
        "5 Château Margaux Margaux 1er 1 Flasche 1988 220",
        "4 Château Lascombes Margaux 2ème 12 Flaschen OHK 1996",
        "51 Château La Lagune Haut Médoc 3ème 2 Magnum 1977",
    ]
    
    print("TESTING PARSING PATTERNS:")
    print("="*80)
    
    for line in test_lines:
        print(f"\nTesting: {line}")
        result = parse_wine_line_improved(line)
        if result:
            print(f"✅ SUCCESS:")
            print(f"   Lot: {result['lot']}")
            print(f"   Wine: {result['wine']}")
            print(f"   Region: {result['region']}")
            print(f"   Quantity: {result['quantity']}")
            print(f"   Unit: {result['unit']} ({result['unit_deciliters']}dl)")
            print(f"   OHK: {result['is_ohk']}")
            print(f"   Year: {result['year']}")
            print(f"   Price: CHF {result['price']}")
            print(f"   Pattern: {result['pattern_used']}")
        else:
            print("❌ FAILED TO PARSE")

def parse_wine_line_improved(line: str) -> dict:
    """Improved parsing with better wine/region separation"""
    
    # Pattern 1: With classification and OHK
    pattern1 = (
        r'^(\d+)\s+'  # Lot number
        r'(Château\s+[^0-9]+?)\s+'  # Wine name (until we hit a region/classification)
        r'([A-Za-zÀ-ÿ\-\s]+?)\s+'  # Region
        r'(\d+(?:er|ème))\s+'  # Classification
        r'(\d+)\s+'  # Quantity
        r'(Flasche|Flaschen|Magnum|Doppelmagnum)\s*'  # Unit
        r'(OHK|OC)?\s*'  # Optional OHK
        r'(\d{4})\s*'  # Year
        r'(\d+(?:\'\d+)*)?'  # Optional price
    )
    
    match = re.match(pattern1, line.strip(), re.IGNORECASE)
    if match:
        lot, wine_raw, region, classification, quantity, unit, ohk, year, price = match.groups()
        
        # Clean wine name and add classification
        wine = f"{wine_raw.strip()} {classification}"
        
        return {
            'lot': lot,
            'wine': wine,
            'region': region.strip(),
            'quantity': int(quantity),
            'unit': unit,
            'unit_deciliters': convert_unit_to_dl(unit),
            'is_ohk': bool(ohk),
            'year': int(year),
            'price': int(price.replace("'", "")) if price else 0,
            'pattern_used': 'improved_classification'
        }
    
    # Pattern 2: Standard without classification
    pattern2 = (
        r'^(\d+)\s+'  # Lot number
        r'(Château\s+[^0-9]+?)\s+'  # Wine name
        r'([A-Za-zÀ-ÿ\-\s]+?)\s+'  # Region  
        r'(\d+)\s+'  # Quantity
        r'(Flasche|Flaschen|Magnum|Doppelmagnum)\s*'  # Unit
        r'(OHK|OC)?\s*'  # Optional OHK
        r'(\d{4})\s*'  # Year
        r'(\d+(?:\'\d+)*)?'  # Optional price
    )
    
    match = re.match(pattern2, line.strip(), re.IGNORECASE)
    if match:
        lot, wine_raw, region, quantity, unit, ohk, year, price = match.groups()
        
        return {
            'lot': lot,
            'wine': wine_raw.strip(),
            'region': region.strip(),
            'quantity': int(quantity),
            'unit': unit,
            'unit_deciliters': convert_unit_to_dl(unit),
            'is_ohk': bool(ohk),
            'year': int(year),
            'price': int(price.replace("'", "")) if price else 0,
            'pattern_used': 'improved_standard'
        }
    
    return None

def convert_unit_to_dl(unit: str) -> float:
    """Convert unit to deciliters"""
    unit_lower = unit.lower()
    if unit_lower in ['flasche', 'flaschen']:
        return 7.5
    elif unit_lower == 'magnum':
        return 15.0
    elif unit_lower == 'doppelmagnum':
        return 30.0
    return 7.5

if __name__ == "__main__":
    test_parsing_patterns()
