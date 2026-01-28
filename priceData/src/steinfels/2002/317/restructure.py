#!/usr/bin/env python3
"""
Simple Text Restructurer for 317.pdf extracted content
"""

import re


def parse_wine_data(text_content):
    """Extract wine data from the OCR text"""
    lines = text_content.split('\n')
    wines = []
    lot_num = 0
    
    # Find all wine entries by looking for structured patterns
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines and headers
        if not line or any(header in line for header in 
                          ['Produkt', 'Menge', 'Jahrgang', 'Zuschlag', 
                           'STEINFELS', 'Ergebnisliste']):
            i += 1
            continue
        
        # Check for lot numbers
        if re.match(r'^\d{1,3}$', line):
            lot_num = int(line)
            i += 1
            continue
        
        # Look for wine names (start with Chateau, Clos, etc.)
        wine_prefixes = ['Chateau', 'Clos', 'Domaine', 'Mixed Lot', 
                        'Aloxe-', 'Beaune', 'Chambertin', 'Pommard']
        
        if any(line.startswith(prefix) for prefix in wine_prefixes):
            wine_name = clean_wine_name(line)
            
            # Look for quantity in next few lines
            quantity = ""
            vintage = ""
            price = ""
            
            for j in range(i + 1, min(i + 8, len(lines))):
                if j >= len(lines):
                    break
                    
                check_line = lines[j].strip()
                
                # Find quantity
                if re.search(r'\d+\s*(Flaschen?|Magnum)', check_line):
                    quantity = check_line
                
                # Find vintage (4-digit year)
                year_match = re.search(r'\b(19\d{2}|20\d{2})\b', check_line)
                if year_match:
                    vintage = year_match.group(1)
                
                # Find price
                price_match = re.search(r"\b(\d{1,2}'\d{3}|\d{3,4})\b", 
                                      check_line)
                if price_match and check_line != vintage:
                    price = price_match.group(1)
            
            if wine_name:
                lot_num += 1
                wines.append({
                    'Lot': lot_num,
                    'Produkt': wine_name,
                    'Menge': quantity,
                    'Jahrgang': vintage,
                    'Zuschlag': price
                })
        
        i += 1
    
    return wines


def clean_wine_name(name):
    """Clean OCR errors in wine names"""
    # Fix common OCR errors
    fixes = [
        ('ChGteau', 'Chateau'),
        ('Chdteau', 'Chateau'),
        ('Ch&teau', 'Chateau'),
        ('Chéteau', 'Chateau'),
        ('Ch@teau', 'Chateau'),
        ('@me', 'ème'),
        ('4me', 'ème'),
        ('2me', 'ème'),
        ('eme', 'ème'),
        ('Saint-Emi', 'Saint-Emilion')
    ]
    
    for old, new in fixes:
        name = name.replace(old, new)
    
    return name.strip()


def main():
    input_file = 'weinauktion_extracted_en.txt'
    output_file = 'wines_structured.txt'
    
    # Read the extracted text
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("Parsing extracted text...")
    wines = parse_wine_data(content)
    
    print(f"Found {len(wines)} wine entries")
    
    # Write structured output
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Lot\tProdukt\tMenge\tJahrgang\tZuschlag\n")
        for wine in wines:
            f.write(f"{wine['Lot']}\t{wine['Produkt']}\t"
                   f"{wine['Menge']}\t{wine['Jahrgang']}\t"
                   f"{wine['Zuschlag']}\n")
    
    # Show preview
    print("\nFirst 10 entries:")
    for i, wine in enumerate(wines[:10]):
        print(f"{i+1:2d}. {wine['Produkt'][:40]:40s} | "
              f"{wine['Menge'][:15]:15s} | {wine['Jahrgang']:4s} | "
              f"{wine['Zuschlag']:6s}")
    
    print(f"\nStructured file created: {output_file}")


if __name__ == "__main__":
    main()
