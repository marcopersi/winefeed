#!/usr/bin/env python3
"""
Steinfels Enhanced Parser with Reference Lists and Text Cleaning
Based on systematic approach with region and producer references
"""

import os
import re
import pdfplumber
import pandas as pd
from typing import Optional, Dict, Tuple
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SteinfelsEnhancedParser:
    def __init__(self):
        """Initialize parser with reference lists and database connection"""
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_ANON_KEY", "")
        )
        
        # Reference lists for better parsing
        self.wine_regions = [
            'Côtes de Bordeaux', 'Lussac-St-Emilion', 'Pomerol', 'Saint Emilion', 'Saint-Emilion', 
            'Haut Médoc', 'Haut-Médoc','Sauternes', 'Margaux', 'Pauillac', 'Pessac Léognan', 
            'Pessac-Léognan', 'Saint Julien', 'Saint-Julien', 'Moulis en Médoc',
            'Moulis-en-Médoc', 'Côtes de Castillon', 'Saint Estéphe', 'Saint-Estéphe', 'Graves', 
            'Lussac-St.Emilion', 'Lussac St Emilion', 'Puisseguin St Emilion', 'Listrac-Médoc', 
            'Listrac', 'Bordeaux', 'Canon Fronsac', 'Premières Côtes de Blaye',
            'Bordeaux Supérieur', 'Côtes de Bourg', 'Listrac Cru Bourgeois',
            'Leroy', 'Bourgogne', 'Rhône', 'Sicilia', 'Columbia', 'Piemont',
            'Toskana', 'Priorat', 'Ribera del Duero', 'Lazio', 'Saint-Estèphe',  
            'Saint Estèphe', 
            # Additional variants
            'Haut Mèdoc', 'Premières Côtes de Bordeaux', 'Hospice de Beaune', 
            'St-Emilion', 
        ]
        
        self.wine_producers = [
            # Längere/spezifischere Namen zuerst (wichtig für korrekte Erkennung)
            'Marchese Antinori', 'Marchesi Antinori', 'Tenuta dell\'Ornellaia',
            'Andrea Costanti', 'Tenuta San Guido', 'Castello di Ama',
            'Verbenna', 'La Torre', 'Cantina Falesco', 'Duca di Salaparuta',
            'Bodegas Palacios', 'Gentaz-Vernieux', 'Guigal', 'Chapoutier',
            'Domaine J-L. Chave', 'Paul Jaboulet Aîné', 'Henri Bonneau', 
            'Château Rayas', 'Château de Beauc', 'Château de Bea', 'Domaine de Vallouit',
            'Domaine de Pegaü', 'Louis Jadot', 'Pio Cesare', 'Bruno Giacosa',
            'Mondavi/Rothschild', 'Frescobaldi/Mondavi',
            'Mondavi', 'Moët et Chandon', 'Cathérine Moine Père & Fils',
            'Domaine Romanée Conti', 'Armand Rousseau', 'Dom.du Château de Meursault',
            'P.Naudin-Varrault', 'Hubert Didier', 'Arthur Barolet',
            'Labaume Ainé & Fils', 'Zibetti', 'Raoul Clerget',
            'Domaine Chantal Lescure', 'Domaine Comte de Vogüé', 'Vincent Girardin',
            'Mahler', 'Moine Père & Fils', 'Domaine Comte Senard',
            'Royé-Labaume & Cie', 'Leroy', 'Château Sainte Michelle', 
            'Antinori', 'Domaine Saier'  # Antinori als letztes, damit spezifischere Namen zuerst erkannt werden
        ]
        
        # Wine classification patterns for extraction (before cleaning)
        self.classification_patterns = [
            r'\b(Grand Cru)\b',                    # Grand Cru
            r'\b(Cru Beaujolais)\b',              # Cru Beaujolais
            r'\b(\d+(?:er|ème))\s+([A-Z])\b',     # 1er A, 2ème B, etc.
            r'\b(\d+(?:er|ème))\b',               # 1er, 2ème, etc.
            r'\b(2e vin de)\b',                   # 2e vin de
        ]
        
        # Text cleaning patterns (applied after classification extraction)
        self.cleanup_patterns = [
            r'\b\d+(?:er|ème)\s+[A-Z]\b',  # Remove "1er A", "2ème B", etc.
            r'\b\d+(?:er|ème)\b',          # Remove remaining "1er", "2ème", etc.
            r'\b(2e vin de)\b',            # Remove "2e vin de"
            r'\b(Grand Cru)\b',            # Remove "Grand Cru"
            r'\b(Cru Beaujolais)\b',       # Remove "Cru Beaujolais"
            r'\([^)]*\)',                  # Remove anything in parentheses
            r'\bigt\b',                    # Remove standalone 'igt'
            r'\b[A-Z]\s*$',               # Remove standalone single letters at end (fallback)
        ]
        
        self.skipped_lines = []
        self.error_lines = []
        
    def setup_reference_tables(self):
        """Setup region and producer reference tables in database"""
        try:
            print("✅ Using local reference lists (DB not available)")
        except Exception as e:
            print(f"⚠️ Could not update reference tables: {e}")

    def extract_classification(self, text: str) -> Tuple[str, str]:
        """
        Extract wine classification from text (Grand Cru, 1er, 2ème, etc.)
        Returns: (remaining_text, extracted_classification)
        """
        classifications = []
        remaining_text = text
        
        for pattern in self.classification_patterns:
            matches = re.finditer(pattern, remaining_text, re.IGNORECASE)
            for match in matches:
                if match.lastindex and match.lastindex > 1:
                    # For patterns with multiple groups (like "1er A")
                    classification = ' '.join(match.groups())
                else:
                    # For single group patterns
                    classification = match.group(1)
                classifications.append(classification)
                
        # Remove all classification patterns from text
        for pattern in self.classification_patterns:
            remaining_text = re.sub(pattern, '', remaining_text, flags=re.IGNORECASE)
            
        # Clean up extra whitespace
        remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
        
        # Join classifications with comma
        classification_str = ', '.join(classifications) if classifications else ""
        
        return remaining_text, classification_str

    def clean_text(self, text: str) -> str:
        """Clean text by removing classifications, parentheses, and unwanted terms"""
        cleaned = text
        
        # Apply cleanup patterns
        for pattern in self.cleanup_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

    def extract_region(self, text: str) -> Tuple[str, str]:
        """
        Extract region from text using reference list
        Returns: (remaining_text, extracted_region)
        """
        text_lower = text.lower()
        
        # Try to find region at end of string first (most common)
        for region in self.wine_regions:
            region_lower = region.lower()
            if text_lower.endswith(region_lower):
                remaining_text = text[:len(text) - len(region)].strip()
                return remaining_text, region
                
        # Try to find region anywhere in string
        for region in self.wine_regions:
            region_lower = region.lower()
            if region_lower in text_lower:
                # Remove region from text
                remaining_text = re.sub(re.escape(region), '', text, flags=re.IGNORECASE).strip()
                remaining_text = re.sub(r'\s+', ' ', remaining_text)
                return remaining_text, region
                
        return text, "Unknown"

    def extract_producer(self, text: str) -> Tuple[str, str]:
        """
        Extract producer from text using reference list
        Returns: (remaining_text, extracted_producer)
        """
        for producer in self.wine_producers:
            if producer.lower() in text.lower():
                # Remove producer from text
                remaining_text = re.sub(re.escape(producer), '', text, flags=re.IGNORECASE).strip()
                remaining_text = re.sub(r'\s+', ' ', remaining_text)
                return remaining_text, producer
                
        return text, ""

    def parse_wine_line_enhanced(self, line: str) -> Optional[Dict]:
        """Enhanced wine line parsing with systematic approach"""
        
        # Skip problematic lines
        if 'mixed' in line.lower() or len(line.strip()) < 10:
            return None
            
        # Skip header lines
        if any(header in line.lower() for header in ['produkt', 'gebiet', 'menge']):
            return None
            
        # Must start with lot number
        lot_match = re.match(r'^(\d+)\s+(.+)$', line.strip())
        if not lot_match:
            return None
            
        lot_number = lot_match.group(1)
        remaining_line = lot_match.group(2)
        
        # Extract price (always at end, if present)
        price = 0
        price_match = re.search(r'(\d+(?:\'\d+)*)$', remaining_line)
        if price_match:
            price = int(price_match.group(1).replace("'", ""))
            remaining_line = remaining_line[:price_match.start()].strip()
            
        # Extract year (4 digits, before price)
        year_match = re.search(r'(\d{4})\s*$', remaining_line)
        if not year_match:
            self.error_lines.append(f"NO_YEAR: {line}")
            return None
            
        year = int(year_match.group(1))
        remaining_line = remaining_line[:year_match.start()].strip()
        
        # Extract OHK (before year)
        is_ohk = False
        ohk_match = re.search(r'\b(OHK|OC)\b\s*$', remaining_line, re.IGNORECASE)
        if ohk_match:
            is_ohk = True
            remaining_line = remaining_line[:ohk_match.start()].strip()
            
        # Extract quantity and unit
        unit_match = re.search(r'(\d+)\s+(Flasche|Flaschen|Magnum|Doppelmagnum)\s*$', 
                              remaining_line, re.IGNORECASE)
        if not unit_match:
            self.error_lines.append(f"NO_UNIT: {line}")
            return None
            
        quantity = int(unit_match.group(1))
        unit = unit_match.group(2)
        remaining_line = remaining_line[:unit_match.start()].strip()
        
        # Now remaining_line contains: Wine Name + Producer + Region + Classification
        # First extract classification (before cleaning)
        after_classification_extraction, classification = self.extract_classification(remaining_line)
        
        # Then clean the text
        cleaned_line = self.clean_text(after_classification_extraction)
        
        # Extract region
        after_region_extraction, region = self.extract_region(cleaned_line)
        
        # Extract producer
        after_producer_extraction, producer = self.extract_producer(after_region_extraction)
        
        # What's left should be the wine name
        wine_name = after_producer_extraction.strip()
        
        # Convert unit to deciliters
        unit_dl = self.convert_unit_to_deciliters(unit)
        
        return {
            'Lot': lot_number,
            'Wine': wine_name,
            'Producer': producer,
            'Region': region,
            'Classification': classification,
            'Quantity': quantity,
            'Unit': unit,
            'Unit_DL': unit_dl,
            'OHK': 'Yes' if is_ohk else 'No',
            'Year': year,
            'Price_CHF': price,
            'Raw_Line': line.strip(),  # Raw_Line direkt nach Spalte K (Price_CHF)
            'Original_Line': remaining_line,  # Before any processing
            'After_Classification': after_classification_extraction,  # After classification extraction
            'Cleaned_Line': cleaned_line,     # After cleaning
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

    def parse_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        """Parse PDF with enhanced approach"""
        print(f"Parsing PDF: {pdf_path}")
        
        # Setup reference tables
        self.setup_reference_tables()
        
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
                
            wine_data = self.parse_wine_line_enhanced(line)
            if wine_data:
                wine_data['Line_Number'] = line_num
                wines.append(wine_data)
                
        # Create DataFrame
        df = pd.DataFrame(wines)
        return df

    def save_to_excel(self, df: pd.DataFrame, pdf_path: str) -> str:
        """Save DataFrame to Excel with comprehensive reporting"""
        base_name = os.path.basename(pdf_path).replace('.pdf', '')
        output_file = f"import/steinfels/prepared/2002/results_{base_name}.xlsx"
        
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Main data sheet
            df.to_excel(writer, sheet_name='Wines', index=False)
            
            # Statistics sheet
            if not df.empty:
                stats_data = {
                    'Metric': ['Total Wines', 'Unique Regions', 'Unique Producers', 
                              'With OHK', 'Average Price', 'Price Range'],
                    'Value': [
                        len(df),
                        len(df['Region'].unique()),
                        len(df[df['Producer'] != '']['Producer'].unique()),
                        len(df[df['OHK'] == 'Yes']),
                        f"CHF {df['Price_CHF'].mean():.2f}",
                        f"CHF {df['Price_CHF'].min()} - {df['Price_CHF'].max()}"
                    ]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                
                # Region breakdown
                region_stats = df['Region'].value_counts().reset_index()
                region_stats.columns = ['Region', 'Count']
                region_stats.to_excel(writer, sheet_name='Region_Stats', index=False)
                
                # Producer breakdown
                producer_stats = df[df['Producer'] != '']['Producer'].value_counts().reset_index()
                producer_stats.columns = ['Producer', 'Count']
                producer_stats.to_excel(writer, sheet_name='Producer_Stats', index=False)
            
            # Error reporting
            if self.error_lines:
                error_df = pd.DataFrame({'Error_Lines': self.error_lines})
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
    """Test enhanced parser on 315.pdf"""
    parser = SteinfelsEnhancedParser()
    
    pdf_file = "import/steinfels/2002/315.pdf"
    
    if os.path.exists(pdf_file):
        print(f"Testing enhanced parser on {pdf_file}...")
        
        df = parser.parse_pdf_to_dataframe(pdf_file)
        
        if not df.empty:
            output_file = parser.save_to_excel(df, pdf_file)
            
            print(f"\n🎉 ENHANCED PARSING SUCCESS!")
            print(f"📊 Parsed {len(df)} wines")
            print(f"📁 Saved to: {output_file}")
            print(f"❌ Error lines: {len(parser.error_lines)}")
            
            # Show improved results
            print(f"\n📋 ENHANCED RESULTS (first 10):")
            for i, row in df.head(10).iterrows():
                producer_str = f" | {row['Producer']}" if row['Producer'] else ""
                ohk_str = " [OHK]" if row['OHK'] == 'Yes' else ""
                print(f"  Lot {row['Lot']}: {row['Wine']}{producer_str} | "
                      f"{row['Region']} | {row['Quantity']}x {row['Unit']} | "
                      f"{row['Year']} | CHF {row['Price_CHF']}{ohk_str}")
                      
            # Show statistics
            print(f"\n📈 STATISTICS:")
            print(f"  Unique regions: {len(df['Region'].unique())}")
            print(f"  Wines with producers: {len(df[df['Producer'] != ''])}")
            print(f"  Average price: CHF {df['Price_CHF'].mean():.2f}")
            
        else:
            print("❌ No wines parsed successfully")
    else:
        print(f"File not found: {pdf_file}")

if __name__ == "__main__":
    main()
