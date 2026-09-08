#!/usr/bin/env python3
"""
Final Steinfels Parser - Optimized for accurate wine name extraction
Focuses on getting the exact format you requested for 315.pdf
"""

import re
import pdfplumber
import pandas as pd
from typing import Optional
import os

class SteinfelsOptimizedParser:
    def __init__(self):
        """Initialize the parser"""
        self.skipped_lines = []
        self.error_lines = []
        
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def parse_wine_line(self, line: str) -> Optional[dict]:
        """
        Parse wine line with focus on correct wine name extraction
        """
        # Skip mixed lot lines
        if 'mixed' in line.lower():
            self.skipped_lines.append(f"MIXED_LOT: {line}")
            return None
            
        # Skip header lines
        if any(header in line.lower() for header in ['produkt', 'gebiet', 'menge', 'jahrgang', 'zuschlag']):
            return None
            
        # Skip lines that don't start with numbers
        if not re.match(r'^\d+\s+', line.strip()):
            return None
            
        # Extract basic components first
        lot_match = re.match(r'^(\d+)\s+(.+)$', line.strip())
        if not lot_match:
            self.error_lines.append(f"NO_LOT_NUMBER: {line}")
            return None
            
        lot_number = lot_match.group(1)
        rest_of_line = lot_match.group(2)
        
        # Extract price (always at the end, if present)
        price = 0
        price_match = re.search(r'(\d+(?:\'\d+)*)$', rest_of_line)
        if price_match:
            price = int(price_match.group(1).replace("'", ""))
            rest_of_line = rest_of_line[:price_match.start()].strip()
            
        # Extract year (4 digits, usually before price)
        year_match = re.search(r'(\d{4})\s*$', rest_of_line)
        if not year_match:
            self.error_lines.append(f"NO_YEAR: {line}")
            return None
            
        year = int(year_match.group(1))
        rest_of_line = rest_of_line[:year_match.start()].strip()
        
        # Extract OHK (if present, before year)
        is_ohk = False
        ohk_match = re.search(r'\b(OHK|OC)\b\s*$', rest_of_line, re.IGNORECASE)
        if ohk_match:
            is_ohk = True
            rest_of_line = rest_of_line[:ohk_match.start()].strip()
            
        # Extract quantity and unit (e.g., "12 Flaschen", "1 Magnum")
        unit_match = re.search(r'(\d+)\s+(Flasche|Flaschen|Magnum|Doppelmagnum)\s*$', rest_of_line, re.IGNORECASE)
        if not unit_match:
            self.error_lines.append(f"NO_UNIT: {line}")
            return None
            
        quantity = int(unit_match.group(1))
        unit = unit_match.group(2)
        rest_of_line = rest_of_line[:unit_match.start()].strip()
        
        # Now rest_of_line should be: "Château NAME REGION [CLASSIFICATION]"
        # We need to separate wine name from region
        
        # Try to extract classification first (1er, 2ème, etc.)
        classification = ""
        classification_match = re.search(r'\b(\d+(?:er|ème))\s*$', rest_of_line)
        if classification_match:
            classification = classification_match.group(1)
            rest_of_line = rest_of_line[:classification_match.start()].strip()
            
        # Now we have: "Château NAME REGION"
        # The trick is to identify where the wine name ends and region begins
        
        # Known regions to help with separation
        known_regions = [
            'Haut-Médoc', 'Haut Médoc', 'Margaux', 'Pauillac', 'Saint-Julien', 
            'Saint Julien', 'Saint-Emilion', 'Saint Emilion', 'Pessac-Léognan',
            'Pomerol', 'Moulis-en-Médoc', 'Côtes de Bordeaux', 'Côtes de Castillon',
            'Premières Côtes de Bordeaux'
        ]
        
        wine_name = ""
        region = ""
        
        # Try to find region at the end
        for known_region in known_regions:
            if rest_of_line.endswith(known_region):
                wine_name = rest_of_line[:-len(known_region)].strip()
                region = known_region
                break
                
        # If no known region found, try to split more intelligently
        if not region:
            # Look for patterns like "Château Name Region"
            parts = rest_of_line.split()
            if len(parts) >= 3:
                # Assume last 1-2 words are region, rest is wine name
                if len(parts[-1]) > 6:  # Single long word is likely region
                    wine_name = " ".join(parts[:-1])
                    region = parts[-1]
                else:  # Last 2 words might be region
                    wine_name = " ".join(parts[:-2])
                    region = " ".join(parts[-2:])
            else:
                wine_name = rest_of_line
                region = "Unknown"
                
        # Add classification to wine name if present
        if classification:
            wine_name = f"{wine_name} {classification}"
            
        # Convert unit to deciliters
        unit_dl = self.convert_unit_to_deciliters(unit)
        
        return {
            'Lot': lot_number,
            'Wine': wine_name.strip(),
            'Region': region.strip(),
            'Quantity': quantity,
            'Unit': unit,
            'Unit_DL': unit_dl,
            'OHK': 'Yes' if is_ohk else 'No',
            'Year': year,
            'Price_CHF': price,
            'Raw_Line': line.strip()
        }

    def convert_unit_to_deciliters(self, unit: str) -> float:
        """Convert unit string to deciliters"""
        unit_lower = unit.lower()
        if unit_lower in ['flasche', 'flaschen']:
            return 7.5  # Standard bottle
        elif unit_lower == 'magnum':
            return 15.0  # Magnum
        elif unit_lower == 'doppelmagnum':
            return 30.0  # Double Magnum
        else:
            return 7.5  # Default to standard bottle

    def parse_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        """Parse PDF and return DataFrame"""
        print(f"Parsing PDF: {pdf_path}")
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            print("No text extracted from PDF")
            return pd.DataFrame()
            
        # Parse wine lines
        wines = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            if not line.strip():
                continue
                
            wine_data = self.parse_wine_line(line)
            if wine_data:
                wines.append(wine_data)
                
        # Create DataFrame
        df = pd.DataFrame(wines)
        return df

    def save_to_excel(self, df: pd.DataFrame, pdf_path: str) -> str:
        """Save DataFrame to Excel with error reporting"""
        base_name = os.path.basename(pdf_path).replace('.pdf', '')
        output_file = f"steinfels_final_{base_name}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Wines', index=False)
            
            # Error reporting sheet
            max_len = max(len(self.skipped_lines), len(self.error_lines)) if (self.skipped_lines or self.error_lines) else 0
            if max_len > 0:
                error_df = pd.DataFrame({
                    'Skipped_Lines': self.skipped_lines + [''] * (max_len - len(self.skipped_lines)),
                    'Error_Lines': self.error_lines + [''] * (max_len - len(self.error_lines))
                })
                error_df.to_excel(writer, sheet_name='Errors', index=False)
            
            # Auto-adjust column widths
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return output_file

def main():
    """Parse 315.pdf with optimized parser"""
    parser = SteinfelsOptimizedParser()
    
    pdf_file = "import/steinfels/2002/315.pdf"
    
    if os.path.exists(pdf_file):
        print(f"Parsing {pdf_file} with optimized parser...")
        
        df = parser.parse_pdf_to_dataframe(pdf_file)
        
        if not df.empty:
            output_file = parser.save_to_excel(df, pdf_file)
            
            print(f"\n🎉 SUCCESS!")
            print(f"📊 Parsed {len(df)} wines")
            print(f"📁 Saved to: {output_file}")
            print(f"⚠️  Skipped lines: {len(parser.skipped_lines)}")
            print(f"❌ Error lines: {len(parser.error_lines)}")
            
            # Show first few results to verify format
            print(f"\n📋 FIRST 10 RESULTS:")
            for i, row in df.head(10).iterrows():
                ohk_str = " [OHK]" if row['OHK'] == 'Yes' else ""
                print(f"  Lot {row['Lot']}: {row['Wine']} | {row['Region']} | "
                      f"{row['Quantity']}x {row['Unit']} | {row['Year']} | "
                      f"CHF {row['Price_CHF']}{ohk_str}")
                      
        else:
            print("❌ No wines parsed successfully")
    else:
        print(f"File not found: {pdf_file}")

if __name__ == "__main__":
    main()
