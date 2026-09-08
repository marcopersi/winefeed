#!/usr/bin/env python3
"""
Steinfels 2002 Robust Parser - Multiple Pattern Approach
Handles complex wine line parsing with multiple pattern attempts
"""

import re
import pdfplumber
import pandas as pd
from typing import List, Dict, Optional, Tuple
from wine_unit_detector import WineUnitDetector
import os

class SteinfelsRobustParser:
    def __init__(self):
        """Initialize the parser with unit detector"""
        self.unit_detector = WineUnitDetector()
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

    def parse_wine_line_v1(self, line: str) -> Optional[Dict]:
        """
        Pattern 1: Standard format with OHK
        Example: 1 Château Le Fournas Bernadotte Haut-Médoc 12 Flaschen OHK 1976 210
        """
        # Pattern: LOT CHÂTEAU_NAME REGION QUANTITY UNIT OHK YEAR PRICE
        pattern = (
            r'^(\d+)\s+'  # Lot number
            r'(Château\s+[^0-9]+?)\s+'  # Wine name (non-greedy until number)
            r'([A-Za-zÀ-ÿ\-\s]+?)\s+'  # Region (non-greedy)
            r'(\d+)\s+'  # Quantity
            r'(Flasche|Flaschen|Magnum|Doppelmagnum)\s*'  # Unit
            r'(OHK|OC)?\s*'  # Optional OHK
            r'(\d{4})\s*'  # Year
            r'(\d+(?:\'\d+)*)?'  # Optional price with apostrophes
        )
        
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            lot, wine, region, quantity, unit, ohk, year, price = match.groups()
            
            # Convert unit to deciliters
            unit_dl = self.convert_unit_to_deciliters(unit)
            
            return {
                'lot': lot,
                'wine': wine.strip(),
                'region': region.strip(),
                'quantity': int(quantity),
                'unit': unit,
                'unit_deciliters': unit_dl,
                'is_ohk': bool(ohk),
                'year': int(year),
                'price': int(price.replace("'", "")) if price else 0,
                'pattern_used': 'v1_standard_ohk'
            }
        return None

    def parse_wine_line_v2(self, line: str) -> Optional[Dict]:
        """
        Pattern 2: Standard format without OHK
        Example: 3 Château Le Fournas Bernadotte Haut-Médoc 8 Flaschen 1976 140
        """
        # Pattern: LOT CHÂTEAU_NAME REGION QUANTITY UNIT YEAR PRICE
        pattern = (
            r'^(\d+)\s+'  # Lot number
            r'(Château\s+[^0-9]+?)\s+'  # Wine name (non-greedy until number)
            r'([A-Za-zÀ-ÿ\-\s]+?)\s+'  # Region (non-greedy)
            r'(\d+)\s+'  # Quantity
            r'(Flasche|Flaschen|Magnum|Doppelmagnum)\s+'  # Unit
            r'(\d{4})\s*'  # Year
            r'(\d+(?:\'\d+)*)?'  # Optional price with apostrophes
        )
        
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            lot, wine, region, quantity, unit, year, price = match.groups()
            
            # Convert unit to deciliters
            unit_dl = self.convert_unit_to_deciliters(unit)
            
            return {
                'lot': lot,
                'wine': wine.strip(),
                'region': region.strip(),
                'quantity': int(quantity),
                'unit': unit,
                'unit_deciliters': unit_dl,
                'is_ohk': False,
                'year': int(year),
                'price': int(price.replace("'", "")) if price else 0,
                'pattern_used': 'v2_standard_no_ohk'
            }
        return None

    def parse_wine_line_v3(self, line: str) -> Optional[Dict]:
        """
        Pattern 3: With classification (1er, 2ème, etc.)
        Example: 5 Château Margaux Margaux 1er 1 Flasche 1988 220
        """
        # Pattern: LOT CHÂTEAU_NAME REGION CLASSIFICATION QUANTITY UNIT YEAR PRICE
        pattern = (
            r'^(\d+)\s+'  # Lot number
            r'(Château\s+[^0-9]+?)\s+'  # Wine name (non-greedy until number)
            r'([A-Za-zÀ-ÿ\-\s]+?)\s+'  # Region (non-greedy)
            r'(\d+(?:er|ème))\s+'  # Classification (1er, 2ème, etc.)
            r'(\d+)\s+'  # Quantity
            r'(Flasche|Flaschen|Magnum|Doppelmagnum)\s*'  # Unit
            r'(OHK|OC)?\s*'  # Optional OHK
            r'(\d{4})\s*'  # Year
            r'(\d+(?:\'\d+)*)?'  # Optional price with apostrophes
        )
        
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            lot, wine, region, classification, quantity, unit, ohk, year, price = match.groups()
            
            # Add classification to wine name
            wine_full = f"{wine.strip()} {classification}"
            
            # Convert unit to deciliters
            unit_dl = self.convert_unit_to_deciliters(unit)
            
            return {
                'lot': lot,
                'wine': wine_full,
                'region': region.strip(),
                'quantity': int(quantity),
                'unit': unit,
                'unit_deciliters': unit_dl,
                'is_ohk': bool(ohk),
                'year': int(year),
                'price': int(price.replace("'", "")) if price else 0,
                'pattern_used': 'v3_with_classification'
            }
        return None

    def parse_wine_line_v4(self, line: str) -> Optional[Dict]:
        """
        Pattern 4: Missing price
        Example: 4 Château Lascombes Margaux 2ème 12 Flaschen OHK 1996
        """
        # Pattern: LOT CHÂTEAU_NAME REGION CLASSIFICATION QUANTITY UNIT OHK YEAR
        pattern = (
            r'^(\d+)\s+'  # Lot number
            r'(Château\s+[^0-9]+?)\s+'  # Wine name (non-greedy until number)
            r'([A-Za-zÀ-ÿ\-\s]+?)\s+'  # Region (non-greedy)
            r'(\d+(?:er|ème))\s+'  # Classification (1er, 2ème, etc.)
            r'(\d+)\s+'  # Quantity
            r'(Flasche|Flaschen|Magnum|Doppelmagnum)\s*'  # Unit
            r'(OHK|OC)?\s*'  # Optional OHK
            r'(\d{4})\s*$'  # Year at end
        )
        
        match = re.match(pattern, line.strip(), re.IGNORECASE)
        if match:
            lot, wine, region, classification, quantity, unit, ohk, year = match.groups()
            
            # Add classification to wine name
            wine_full = f"{wine.strip()} {classification}"
            
            # Convert unit to deciliters
            unit_dl = self.convert_unit_to_deciliters(unit)
            
            return {
                'lot': lot,
                'wine': wine_full,
                'region': region.strip(),
                'quantity': int(quantity),
                'unit': unit,
                'unit_deciliters': unit_dl,
                'is_ohk': bool(ohk),
                'year': int(year),
                'price': 0,  # No price
                'pattern_used': 'v4_no_price'
            }
        return None

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

    def parse_wine_line(self, line: str) -> Optional[Dict]:
        """
        Parse wine line using multiple pattern attempts
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
            
        # Try each pattern in order
        patterns = [
            self.parse_wine_line_v1,  # Standard with OHK
            self.parse_wine_line_v2,  # Standard without OHK  
            self.parse_wine_line_v3,  # With classification
            self.parse_wine_line_v4,  # Missing price
        ]
        
        for pattern_func in patterns:
            result = pattern_func(line)
            if result:
                return result
                
        # If no pattern matched, add to error lines
        self.error_lines.append(f"NO_PATTERN_MATCH: {line}")
        return None

    def parse_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        """Parse PDF and return DataFrame with robust parsing"""
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
                wine_data['line_number'] = line_num
                wine_data['raw_line'] = line.strip()
                wines.append(wine_data)
                
        # Create DataFrame
        df = pd.DataFrame(wines)
        
        # Reorder columns for better readability
        if not df.empty:
            column_order = [
                'lot', 'wine', 'region', 'quantity', 'unit', 'unit_deciliters',
                'is_ohk', 'year', 'price', 'pattern_used', 'line_number', 'raw_line'
            ]
            df = df[column_order]
            
        return df

    def save_to_excel(self, df: pd.DataFrame, pdf_path: str) -> str:
        """Save DataFrame to Excel with error reporting"""
        base_name = os.path.basename(pdf_path).replace('.pdf', '')
        output_file = f"steinfels_parsed_{base_name}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Wines', index=False)
            
            # Error reporting sheet
            error_data = {
                'Skipped_Lines': self.skipped_lines,
                'Error_Lines': self.error_lines
            }
            
            max_len = max(len(self.skipped_lines), len(self.error_lines))
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
    """Test the robust parser on 315.pdf"""
    parser = SteinfelsRobustParser()
    
    pdf_file = "import/steinfels/2002/315.pdf"
    
    if os.path.exists(pdf_file):
        print(f"Parsing {pdf_file} with robust multi-pattern approach...")
        
        df = parser.parse_pdf_to_dataframe(pdf_file)
        
        if not df.empty:
            output_file = parser.save_to_excel(df, pdf_file)
            
            print(f"\n🎉 SUCCESS!")
            print(f"📊 Parsed {len(df)} wines")
            print(f"📁 Saved to: {output_file}")
            print(f"⚠️  Skipped lines: {len(parser.skipped_lines)}")
            print(f"❌ Error lines: {len(parser.error_lines)}")
            
            # Show sample results
            print(f"\n📋 SAMPLE RESULTS:")
            for i, row in df.head(5).iterrows():
                ohk_str = " [OHK]" if row['is_ohk'] else ""
                print(f"  Lot {row['lot']}: {row['wine']} ({row['region']}) "
                      f"- {row['quantity']}x {row['unit']} {row['year']} "
                      f"CHF {row['price']}{ohk_str} [{row['pattern_used']}]")
                      
            # Show pattern usage statistics
            print(f"\n📈 PATTERN USAGE:")
            pattern_counts = df['pattern_used'].value_counts()
            for pattern, count in pattern_counts.items():
                print(f"  {pattern}: {count}")
                
        else:
            print("❌ No wines parsed successfully")
    else:
        print(f"File not found: {pdf_file}")

if __name__ == "__main__":
    main()
