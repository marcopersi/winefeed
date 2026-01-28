#!/usr/bin/env python3
"""
Steinfels Parser for 320.pdf (2003)
Based on successful 319 parser with corrected save path
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

class SteinfelsParser320:
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
            # Abkürzungen und Varianten
            'Haut-Mé', 'Pauill', 'St-Em', 'St-Jul', 'Pessac-Léo',
        ]
        
        # Mapping für abgekürzte Regionen
        self.region_mappings = {
            'Haut-Mé': 'Haut-Médoc',
            'Pauill': 'Pauillac',
            'St-Em': 'Saint-Emilion',
            'St-Jul': 'Saint-Julien',
            'Pessac-Léo': 'Pessac-Léognan',
            'Saint-Emilio': 'Saint-Emilion',
        }
        
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
            'Collection Dr. Barolet', 'Bouchard Âiné & Fils', 'Paul Bouchard & Cie',
            'Bouchard Père & Fils', 'Bouchard Père & Fil', 'Paul Bouchard & Ci',
            'P.Naudin-Varrault', 'J. Hubert-Didier', 'Hubert Didier', 'Arthur Barolet',
            'Michel Noëllat', 'Drouhin-Laroze', 'G. de Buyssières',
            'Etienne Sauzet', 'Jean-Marie Garnier', 'Taittinger',
            'Angelo Gaja', 'Carlo Boffa', 'Sottimano', 'Conterno Fantino',
            'Luciano Sandro', 'Scavino', 'Castello dei Rampolla', 'Dominus Estate',
            'Labaume Ainé & Fils', 'Zibetti', 'Raoul Clerget',
            'Domaine Chantal Lescure', 'Domaine Comte de Vogüé', 'Vincent Girardin',
            'Mahler', 'Moine Père & Fils', 'Domaine Comte Senard', 'Louis Latour',
            'Royé-Labaume & Cie', 'Leroy', 'Château Sainte Michelle', 'Comte Georges',
            'Antinori', 'Domaine Saier', 'Produttori del Barbaresco'  # Antinori als letztes
        ]
        
        # Wine classification patterns for extraction (before cleaning)
        self.classification_patterns = [
            r'\b(Grand\s+Cru\s+Classé)\b',        # Grand Cru Classé
            r'\b(Grand\s+Cru)\b',                 # Grand Cru
            r'\b(Cru\s+Classé)\b',                # Cru Classé  
            r'\b(Cru\s+Beaujolais)\b',            # Cru Beaujolais
            r'\b(Cru\s+Bourgeois)\b',             # Cru Bourgeois
            r'\b(\d+(?:er|ème)\s+Cru\s+Classé)\b', # 1er Cru Classé
            r'\b(\d+(?:er|ème)\s+Cru)\b',         # 1er Cru, 2ème Cru, 3ème Cru etc.
            r'\b(\d+(?:er|ème))\s+(Cru\s+[AB])\b',  # 1er Cru A, 2ème Cru B
            r'\b(\d+(?:er|ème))\s+([AB])\b',      # 1er A, 2ème B, etc.
            r'\b(\d+(?:er|ème))\b',               # 1er, 2ème, etc.
            r'\b(2e\s+vin\s+de)\b',               # 2e vin de
        ]
        
        # Text cleaning patterns (applied after classification extraction)
        self.cleanup_patterns = [
            r'\b\d+(?:er|ème)\s+Cru\s+[AB]\b',  # Remove "1er Cru A", "2ème Cru B" FIRST
            r'\b\d+(?:er|ème)\s+Cru\b',         # Remove "1er Cru", "2ème Cru", "3ème Cru"
            r'\b(Cru\s+[AB])\b',                # Remove remaining "Cru A", "Cru B"
            r'\bCru\b',                         # Remove standalone "Cru"
            r'\b\d+(?:er|ème)\s+[AB]\b',        # Remove "1er A", "2ème B", etc.
            r'\b\d+(?:er|ème)\b',               # Remove remaining "1er", "2ème", etc.
            r'\b(2e vin de)\b',                 # Remove "2e vin de"
            r'\b(Grand Cru)\b',                 # Remove "Grand Cru"
            r'\b(Cru Beaujolais)\b',            # Remove "Cru Beaujolais"
            r'\b(Cru Bourgeois)\b',             # Remove "Cru Bourgeois"
            # NOTE: Do NOT remove Saint-Emilio here - it's handled in region mapping
            r'\([^)]*\)',                       # Remove anything in parentheses
            r'\bigt\b',                         # Remove standalone 'igt'
            r'\b[A-Z]\s*$',                    # Remove standalone single letters at end
        ]
        
        self.skipped_lines = []
        self.error_lines = []
        
    def setup_reference_tables(self):
        """Setup region and producer reference tables in database"""
        try:
            print("✅ Using local reference lists (DB not available)")
        except Exception as e:
            print(f"⚠️ Could not update reference tables: {e}")

    def convert_unit_to_deciliters(self, quantity_text: str) -> float:
        """Convert wine unit quantities to deciliters - returns unit size only"""
        try:
            # Normalize text
            text = quantity_text.lower().strip()
            
            # Look for patterns like "24 3/8 Flaschen" or "6 3/8 Flaschen"
            fraction_pattern = r'(\d+)\s+(\d+)/(\d+)\s*(flaschen|magnum|jéroboam)'
            fraction_match = re.search(fraction_pattern, text, re.IGNORECASE)
            
            if fraction_match:
                numerator = int(fraction_match.group(2))
                denominator = int(fraction_match.group(3))
                
                # Calculate fraction size: 3/8 = 0.375L = 3.75dl
                fraction_size_dl = (numerator / denominator) * 10
                
                # Return only the unit size, not multiplied by quantity
                return fraction_size_dl
            
            # Look for standalone fractions like "3/8 Flaschen"
            standalone_fraction_pattern = r'(\d+)/(\d+)\s*(flaschen|magnum|jéroboam)'
            standalone_match = re.search(standalone_fraction_pattern, text, 
                                       re.IGNORECASE)
            
            if standalone_match:
                numerator = int(standalone_match.group(1))
                denominator = int(standalone_match.group(2))
                
                # Convert fraction to dl: 3/8 = 0.375L = 3.75dl
                fraction_size_dl = (numerator / denominator) * 10
                return fraction_size_dl
            
            # Unit type detection - return only unit size, not multiplied
            if 'magnum' in text:
                return 15.0  # 1.5L = 15dl
            elif 'jéroboam' in text or 'jeroboam' in text:
                return 30.0  # 3L = 30dl (or 45dl for Champagne)
            elif 'mathusalem' in text:
                return 60.0  # 6L = 60dl
            else:
                return 7.5   # Standard bottle = 0.75L = 7.5dl
                
        except Exception as e:
            print(f"Warning: Could not convert unit '{quantity_text}': {e}")
            return 7.5  # Default to standard bottle
    
    def parse_wine_line_enhanced(self, line: str) -> Optional[Dict]:
        """Parse wine line with systematic step-by-step approach"""
        
        # Check if line contains wine data
        if not re.search(r'\d+.*(?:Flaschen?|Magnum|Jéroboam|Mathusalem)', line, 
                        re.IGNORECASE):
            return None
        
        # Skip lines that look like headers or summaries
        if any(word in line.lower() for word in ['lot', 'total', 'summe', 'seite']):
            return None
        
        try:
            # Step 1: Extract lot number and remaining text
            lot_match = re.match(r'^(\d+)\s+(.+)$', line.strip())
            if not lot_match:
                return None
            
            lot_number = lot_match.group(1)
            remaining_text = lot_match.group(2).strip()
            
            # Step 2: Remove quantity (including OHK) from beginning
            quantity_pattern = r'(\d+(?:\s+\d+/\d+)?\s*(?:Flaschen?|Magnum|Jéroboam|Mathusalem)(?:\s+OHK)?)'
            quantity_match = re.search(quantity_pattern, remaining_text, 
                                     re.IGNORECASE)
            
            if not quantity_match:
                return None
            
            quantity_text = quantity_match.group(1)
            
            # Check for OHK in quantity text
            is_ohk = 'ohk' in quantity_text.lower()
            
            # Remove quantity from text
            remaining_text = remaining_text.replace(quantity_text, '', 1).strip()
            
            # Step 3: Extract and remove classifications until first digit
            extracted_classifications = []
            
            # Keep extracting classifications until we hit a digit
            while True:
                found_classification = False
                
                for pattern in self.classification_patterns:
                    match = re.search(pattern, remaining_text, re.IGNORECASE)
                    if match:
                        # Check if this classification comes before any 4-digit year
                        year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b', 
                                             remaining_text)
                        if not year_match or match.start() < year_match.start():
                            classification = match.group(1) if match.lastindex == 1 else ' '.join(match.groups())
                            extracted_classifications.append(classification)
                            remaining_text = remaining_text[:match.start()] + remaining_text[match.end():]
                            remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
                            found_classification = True
                            break
                
                if not found_classification:
                    break
            
            # Step 4: Clean thousand separators
            remaining_text = re.sub(r"(\d)'(\d{3})", r'\1\2', remaining_text)
            
            # Step 5: Extract price from end (after cleaning separators)
            price = 0
            price_match = re.search(r'(\d+)\s*$', remaining_text)
            if price_match:
                price = int(price_match.group(1))
                remaining_text = remaining_text[:price_match.start()].strip()
            
            # Step 6: Extract vintage from end
            year = None
            year_match = re.search(r'\b(19\d{2}|20[0-2]\d)\b\s*$', remaining_text)
            if year_match:
                year = int(year_match.group(1))
                remaining_text = remaining_text[:year_match.start()].strip()
            
            # Step 7: What remains is the wine name
            wine_name = remaining_text.strip()
            
            # Step 8: Extract region and producer from wine name
            region = "Unknown"
            producer = ""
            
            # Try to extract region
            for wine_region in self.wine_regions:
                if wine_region.lower() in wine_name.lower():
                    region = self.region_mappings.get(wine_region, wine_region)
                    # Remove region from wine name
                    wine_name = re.sub(re.escape(wine_region), '', wine_name, 
                                     flags=re.IGNORECASE).strip()
                    wine_name = re.sub(r'\s+', ' ', wine_name)
                    break
            
            # Try to extract producer
            for wine_producer in self.wine_producers:
                if wine_producer.lower() in wine_name.lower():
                    producer = wine_producer
                    # Remove producer from wine name
                    wine_name = re.sub(re.escape(wine_producer), '', wine_name, 
                                     flags=re.IGNORECASE).strip()
                    wine_name = re.sub(r'\s+', ' ', wine_name)
                    break
            
            # Convert unit to deciliters
            unit_dl = self.convert_unit_to_deciliters(quantity_text)
            
            # Parse quantity for the Quantity field
            quantity_num_match = re.search(r'^(\d+)', quantity_text)
            quantity = int(quantity_num_match.group(1)) if quantity_num_match else 1
            
            return {
                'Lot': lot_number,
                'Wine': wine_name,
                'Producer': producer,
                'Region': region,
                'Classification': ', '.join(extracted_classifications) if extracted_classifications else "",
                'Quantity': quantity,
                'Unit': unit_dl,
                'OHK': 'Yes' if is_ohk else 'No',
                'Year': year,
                'Price_CHF': price,
                'Raw_Line': line.strip()
            }
            
        except Exception as e:
            self.error_lines.append(f"PARSE_ERROR: {line} | Error: {str(e)}")
            return None

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = ""
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                
                print(f"Extracted {len(text)} characters from PDF")
                return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def parse_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        """Parse PDF to DataFrame using systematic approach"""
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
        # CORRECTED PATH: Save to prepared folder
        output_file = f"import/steinfels/prepared/2003/results_{base_name}.xlsx"
        
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
                if len(df[df['Producer'] != '']) > 0:
                    producer_stats = df[df['Producer'] != '']['Producer'].value_counts().reset_index()
                    producer_stats.columns = ['Producer', 'Count']
                    producer_stats.to_excel(writer, sheet_name='Producer_Stats', index=False)
            
            # Error reporting
            if self.error_lines:
                error_df = pd.DataFrame({'Error_Lines': self.error_lines})
                error_df.to_excel(writer, sheet_name='Errors', index=False)
        
        return output_file

def main():
    """Parse 320.pdf using systematic approach"""
    parser = SteinfelsParser320()
    
    pdf_file = "import/steinfels/source/2003/320.pdf"
    
    if os.path.exists(pdf_file):
        print(f"Testing parser 320 on {pdf_file}...")
        
        df = parser.parse_pdf_to_dataframe(pdf_file)
        
        if not df.empty:
            output_file = parser.save_to_excel(df, pdf_file)
            
            print(f"\n🎉 PARSING SUCCESS!")
            print(f"📊 Parsed {len(df)} wines")
            print(f"📁 Saved to: {output_file}")
            print(f"❌ Error lines: {len(parser.error_lines)}")
            
            # Show results
            print(f"\n📋 RESULTS (first 10):")
            for i, row in df.head(10).iterrows():
                producer_str = f" | {row['Producer']}" if row['Producer'] else ""
                classification_str = f" [{row['Classification']}]" if row['Classification'] else ""
                ohk_str = " [OHK]" if row['OHK'] == 'Yes' else ""
                print(f"  Lot {row['Lot']}: {row['Wine']}{producer_str} | "
                      f"{row['Region']}{classification_str} | {row['Unit']} | "
                      f"{row['Year']} | CHF {row['Price_CHF']}{ohk_str}")
                      
            # Show statistics
            print(f"\n📈 STATISTICS:")
            print(f"  Unique regions: {len(df['Region'].unique())}")
            print(f"  Wines with producers: {len(df[df['Producer'] != ''])}")
            print(f"  Wines with classifications: {len(df[df['Classification'] != ''])}")
            print(f"  Average price: CHF {df['Price_CHF'].mean():.2f}")
            
        else:
            print("❌ No wines parsed successfully")
    else:
        print(f"File not found: {pdf_file}")

if __name__ == "__main__":
    main()
