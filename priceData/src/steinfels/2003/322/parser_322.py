#!/usr/bin/env python3
"""
Steinfels Parser 319 - Based on successful 315 parser
Simple and reliable approach with proven reference lists
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

class SteinfelsParser322:
    def __init__(self):
        """Initialize parser with reference lists and database connection"""
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_ANON_KEY", "")
        )
        
        # Reference lists for better parsing (from 315)
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
            'St-Emilion', 'Saint-Emilio',  # ADD Saint-Emilio here
            # Abkürzungen und Varianten
            'Haut-Mé', 'Pauill', 'St-Em', 'St-Jul', 'Pessac-Léo',
        ]
        
        # Mapping für abgekürzte Regionen
        self.region_mappings = {
            'Haut-Mé': 'Haut-Médoc',
            'Haut-Médoc': 'Haut-Médoc',
            'Pauill': 'Pauillac',
            'Pau': 'Pauillac',
            'St-Em': 'Saint-Emilion',
            'Saint-Estè': 'Saint-Estéphe',
            'St-Jul': 'Saint-Julien',
            'Pessac-Léo': 'Pessac-Léognan',
            'Saint-Emilio': 'Saint-Emilion',
            'Moulis-en-Méd': 'Moulis-en-Médoc',
            'Saint': 'Saint-Emilion'
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
            'Collection Dr. Barolet', 'Bouchard Père & Fils', 'Bouchard Père & Fil',
            'P.Naudin-Varrault', 'J. Hubert-Didier', 'Hubert Didier', 'Arthur Barolet',
            'Michel Noëllat', 'Drouhin-Laroze', 'G. de Buyssières',
            'Etienne Sauzet', 'Jean-Marie Garnier', 'Taittinger',
            'Angelo Gaja', 'Paul Jaboulet', 'Carlo Boffa', 'Sottimano', 'Conterno Fantino',
            'Luciano Sandro', 'Scavino', 'Castello dei Rampolla', 'Dominus Estate',
            'Labaume Ainé & Fils', 'Zibetti', 'Raoul Clerget', 'Avignonesi',
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

    def extract_classification(self, text: str) -> Tuple[str, str]:
        """
        Extract wine classification from text (Grand Cru, 1er, 2ème, etc.)
        Returns: (remaining_text, extracted_classification)
        """
        classifications = []
        remaining_text = text
        
        for pattern in self.classification_patterns:
            matches = re.findall(pattern, remaining_text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    classification = ' '.join(match).strip()
                else:
                    classification = match.strip()
                if classification and classification not in classifications:
                    classifications.append(classification)
        
        # Remove classification terms from text for cleaner wine name
        for pattern in self.cleanup_patterns:
            remaining_text = re.sub(pattern, ' ', remaining_text, flags=re.IGNORECASE)
        
        # Clean up extra spaces
        remaining_text = ' '.join(remaining_text.split())
        
        return remaining_text, ' | '.join(classifications)
    
    def extract_region(self, text: str) -> str:
        """Extract wine region from text using reference list"""
        # Check direct matches first
        for region in self.wine_regions:
            if region.lower() in text.lower():
                return region
        
        # Check mappings for abbreviations
        for abbrev, full_name in self.region_mappings.items():
            if abbrev.lower() in text.lower():
                return full_name
        
        return ""
    
    def extract_producer(self, text: str) -> str:
        """Extract wine producer from text using reference list"""
        for producer in self.wine_producers:
            if producer.lower() in text.lower():
                return producer
        return ""
    
    def extract_vintage(self, text: str) -> str:
        """Extract vintage year from text"""
        vintage_pattern = r'\b(19\d{2}|20[0-2]\d)\b'
        matches = re.findall(vintage_pattern, text)
        return matches[0] if matches else ""
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF using pdfplumber"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                full_text = ""
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        full_text += text + "\n"
                
                return full_text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""
    
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
        if not re.search(r'\d+.*(?:Flaschen?|Magnum|Jéroboam|Mathusalem)', line, re.IGNORECASE):
            return None
        
        try:
            # Extract lot number
            lot_match = re.match(r'^(\d+)\s+(.+)', line)
            if not lot_match:
                return None
                
            lot_number = int(lot_match.group(1))
            remaining_text = lot_match.group(2).strip()
            
            # STEP 1: Extract and remove quantity
            quantity_pattern = r'(\d+(?:\s+\d+/\d+)?\s*(?:Flaschen?|Magnum|Jéroboam|Mathusalem)(?:\s+OHK)?)'
            quantity_match = re.search(quantity_pattern, remaining_text, re.IGNORECASE)
            
            if not quantity_match:
                return None
            
            quantity_text = quantity_match.group(1)
            unit_dl = self.convert_unit_to_deciliters(quantity_text)
            
            # Check for OHK in quantity text
            ohk = "Yes" if "OHK" in quantity_text.upper() else "No"
            
            # Extract bottle count
            bottle_count_match = re.search(r'(\d+(?:\s+\d+/\d+)?)', quantity_text)
            bottle_count = 1
            if bottle_count_match:
                count_text = bottle_count_match.group(1).strip()
                if '/' in count_text:
                    if ' ' in count_text:  # "24 3/8"
                        parts = count_text.split()
                        main_num = int(parts[0])
                        fraction_parts = parts[1].split('/')
                        fraction_val = int(fraction_parts[0]) / int(fraction_parts[1])
                        bottle_count = main_num + fraction_val
                    else:  # "3/8"
                        fraction_parts = count_text.split('/')
                        bottle_count = int(fraction_parts[0]) / int(fraction_parts[1])
                else:
                    bottle_count = int(count_text)
            
            # Remove quantity from text
            remaining_text = remaining_text.replace(quantity_text, '', 1).strip()
            
            # No need to check for OHK again - already handled above
            
            # STEP 2: Extract classification and remove everything until first digit
            classification = ""
            for pattern in self.classification_patterns:
                match = re.search(pattern, remaining_text, re.IGNORECASE)
                if match:
                    if isinstance(match.groups(), tuple) and len(match.groups()) > 1:
                        classification = ' '.join(match.groups()).strip()
                    else:
                        classification = match.group(1).strip()
                    
                    # Remove classification and everything after it until first digit
                    start_pos = match.start()
                    # Find next digit after the classification
                    text_after_class = remaining_text[match.end():]
                    next_digit_match = re.search(r'\d', text_after_class)
                    if next_digit_match:
                        end_pos = match.end() + next_digit_match.start()
                        remaining_text = remaining_text[:start_pos] + remaining_text[end_pos:]
                    else:
                        remaining_text = remaining_text[:start_pos]
                    
                    remaining_text = re.sub(r'\s+', ' ', remaining_text).strip()
                    break
            
            # STEP 3: Clean thousand separators
            remaining_text = remaining_text.replace("'", "").replace("'", "")
            
            # STEP 4: Extract price from end (1-5 digits before space or end)
            price_chf = 0.0
            price_match = re.search(r'\b(\d{1,5})\s*$', remaining_text)
            if price_match:
                price_chf = float(price_match.group(1))
                remaining_text = remaining_text[:price_match.start()].strip()
            
            # STEP 5: Extract vintage from end (exactly 4 digits)
            vintage = None
            vintage_match = re.search(r'\b(19\d{2}|20\d{2})\s*$', remaining_text)
            if vintage_match:
                vintage = vintage_match.group(1)
                remaining_text = remaining_text[:vintage_match.start()].strip()
            
            # STEP 6: Extract region and producer from remaining text
            region = self.extract_region(remaining_text)
            producer = self.extract_producer(remaining_text)
            
            # Clean wine name (what's left is the wine name)
            cleaned_wine = remaining_text
            if region:
                cleaned_wine = cleaned_wine.replace(region, '').strip()
            if producer:
                cleaned_wine = cleaned_wine.replace(producer, '').strip()
            
            # Final cleanup
            cleaned_wine = ' '.join(cleaned_wine.split())
            cleaned_wine = cleaned_wine.strip(',-. ')
            
            return {
                'Lot': lot_number,
                'Wine': cleaned_wine,
                'Region': region,
                'Producer': producer,
                'Classification': classification,
                'Year': vintage,
                'Bottle_Count': bottle_count,
                'Unit': unit_dl,
                'Price_CHF': price_chf,
                'OHK': ohk,
                'Original_Line': line
            }
            
        except Exception as e:
            self.error_lines.append(f"Error parsing line: {line} - {str(e)}")
            return None

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
            
        print(f"Extracted {len(text)} characters from PDF")
        
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
                
                # Region analysis
                region_stats = df['Region'].value_counts().reset_index()
                region_stats.columns = ['Region', 'Count']
                region_stats.to_excel(writer, sheet_name='Region_Stats', index=False)
                
                # Producer analysis 
                producer_stats = df[df['Producer'] != '']['Producer'].value_counts().reset_index()
                producer_stats.columns = ['Producer', 'Count']
                producer_stats.to_excel(writer, sheet_name='Producer_Stats', index=False)
            
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
        
        print(f"Excel file saved: {output_file}")
        return output_file


def main():
    """Test parser on 322.pdf"""
    parser = SteinfelsParser322()
    
    # Use absolute path
    pdf_file = "/Users/marcopersi/development/winefeed/priceData/import/steinfels/source/2003/322.pdf"

    if os.path.exists(pdf_file):
        print(f"Testing parser 322 on {pdf_file}...")

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
