#!/usr/bin/env python3
"""
Base Parser Template for Steinfels PDFs
Provides common functionality for all Steinfels parsers with Template Method pattern
"""

import os
import re
import pdfplumber
import pandas as pd
from typing import Optional, Dict, Tuple, List
from supabase import create_client, Client
from dotenv import load_dotenv
from abc import ABC, abstractmethod

# Load environment variables
load_dotenv()


class BaseSteinfelsParser(ABC):
    """Base class for all Steinfels parsers using Template Method pattern"""

    def __init__(self):
        """Initialize parser with reference lists and database connection"""
        self.supabase: Client = create_client(
            os.getenv("SUPABASE_URL", ""),
            os.getenv("SUPABASE_ANON_KEY", "")
        )

        # Common reference lists - can be overridden by subclasses
        self.wine_regions = self.get_wine_regions()
        self.wine_producers = self.get_wine_producers()
        self.classification_patterns = self.get_classification_patterns()
        self.cleanup_patterns = self.get_cleanup_patterns()
        self.region_mappings = self.get_region_mappings()

        self.skipped_lines = []
        self.error_lines = []

    # Template methods - common implementation
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
        """Parse PDF with enhanced approach - Template Method"""
        print(f"Parsing PDF: {pdf_path}")

        # Setup reference tables
        self.setup_reference_tables()

        # Extract raw text
        raw_text = self.extract_text_from_pdf(pdf_path)
        if not raw_text:
            print("❌ No text extracted from PDF")
            return pd.DataFrame()

        # Parse lines
        lines = raw_text.split('\n')
        parsed_data = []

        for line in lines:
            line = line.strip()
            if not line or len(line) < 10:
                continue

            parsed_line = self.parse_line(line)
            if parsed_line:
                parsed_data.append(parsed_line)

        # Create DataFrame
        if parsed_data:
            df = pd.DataFrame(parsed_data)
            print(f"✅ Successfully parsed {len(df)} wines")
            return df
        else:
            print("❌ No data parsed")
            return pd.DataFrame()

    def convert_unit_to_deciliters(self, unit: str) -> Optional[float]:
        """Convert various unit formats to deciliters"""
        if not unit:
            return None

        unit = unit.lower().strip()

        # Direct deciliter values
        if 'dl' in unit:
            match = re.search(r'(\d+(?:[.,]\d+)?)', unit)
            if match:
                return float(match.group(1).replace(',', '.'))

        # Centiliters to deciliters
        if 'cl' in unit:
            match = re.search(r'(\d+(?:[.,]\d+)?)', unit)
            if match:
                cl_value = float(match.group(1).replace(',', '.'))
                return cl_value / 10

        # Liters to deciliters
        if 'l' in unit or 'ltr' in unit:
            match = re.search(r'(\d+(?:[.,]\d+)?)', unit)
            if match:
                l_value = float(match.group(1).replace(',', '.'))
                return l_value * 10

        # Bottle formats
        bottle_sizes = {
            'magnum': 15.0,
            'doppelmagnum': 30.0,
            'jeroboam': 30.0,
            'imperial': 60.0,
            'mathusalem': 60.0,
        }

        for bottle_type, size_dl in bottle_sizes.items():
            if bottle_type in unit:
                return size_dl

        return None

    def extract_classification(self, text: str) -> Tuple[str, str]:
        """Extract wine classification from text (Grand Cru, 1er, 2ème, etc.)"""
        classifications = []
        remaining_text = text

        for pattern in self.classification_patterns:
            matches = list(re.finditer(pattern, remaining_text, re.IGNORECASE))
            for match in matches:
                classifications.append(match.group(0))

        classification = ' '.join(classifications) if classifications else ''
        return remaining_text, classification

    def clean_text(self, text: str) -> str:
        """Clean text by removing classification markers and noise"""
        cleaned = text

        for pattern in self.cleanup_patterns:
            cleaned = re.sub(pattern, ' ', cleaned, flags=re.IGNORECASE)

        # Remove extra whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def extract_region(self, text: str) -> Tuple[str, str]:
        """Extract wine region from text"""
        remaining_text = text
        extracted_region = ''

        # Sort regions by length (longest first) for better matching
        sorted_regions = sorted(self.wine_regions, key=len, reverse=True)

        for region in sorted_regions:
            pattern = r'\b' + re.escape(region) + r'\b'
            if re.search(pattern, remaining_text, re.IGNORECASE):
                extracted_region = region
                remaining_text = re.sub(pattern, '', remaining_text, flags=re.IGNORECASE)
                break

        # Apply region mappings if configured
        if extracted_region in self.region_mappings:
            extracted_region = self.region_mappings[extracted_region]

        return remaining_text.strip(), extracted_region

    def extract_producer(self, text: str) -> Tuple[str, str]:
        """Extract wine producer from text"""
        remaining_text = text
        extracted_producer = ''

        # Sort producers by length (longest first) for better matching
        sorted_producers = sorted(self.wine_producers, key=len, reverse=True)

        for producer in sorted_producers:
            pattern = r'\b' + re.escape(producer) + r'\b'
            if re.search(pattern, remaining_text, re.IGNORECASE):
                extracted_producer = producer
                remaining_text = re.sub(pattern, '', remaining_text, flags=re.IGNORECASE)
                break

        return remaining_text.strip(), extracted_producer

    def setup_reference_tables(self):
        """Setup region and producer reference tables in database"""
        try:
            print("✅ Using local reference lists (DB not available)")
        except Exception as e:
            print(f"⚠️ Could not update reference tables: {e}")

    # Hook methods - can be overridden by subclasses
    def get_wine_regions(self) -> List[str]:
        """Return list of wine regions - override for parser-specific regions"""
        return [
            'Côtes de Bordeaux', 'Lussac-St-Emilion', 'Pomerol', 'Saint Emilion', 'Saint-Emilion',
            'Haut Médoc', 'Haut-Médoc', 'Sauternes', 'Margaux', 'Pauillac', 'Pessac Léognan',
            'Pessac-Léognan', 'Saint Julien', 'Saint-Julien', 'Moulis en Médoc',
            'Moulis-en-Médoc', 'Côtes de Castillon', 'Saint Estéphe', 'Saint-Estéphe', 'Graves',
            'Lussac-St.Emilion', 'Lussac St Emilion', 'Puisseguin St Emilion', 'Listrac-Médoc',
            'Listrac', 'Bordeaux', 'Canon Fronsac', 'Premières Côtes de Blaye',
            'Bordeaux Supérieur', 'Côtes de Bourg', 'Listrac Cru Bourgeois',
            'Leroy', 'Bourgogne', 'Rhône', 'Sicilia', 'Columbia', 'Piemont',
            'Toskana', 'Priorat', 'Ribera del Duero', 'Lazio', 'Saint-Estèphe',
            'Saint Estèphe', 'Haut Mèdoc', 'Premières Côtes de Bordeaux',
            'Hospice de Beaune', 'St-Emilion',
        ]

    def get_wine_producers(self) -> List[str]:
        """Return list of wine producers - override for parser-specific producers"""
        return [
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
            'Antinori', 'Domaine Saier'
        ]

    def get_classification_patterns(self) -> List[str]:
        """Return classification patterns - override for parser-specific patterns"""
        return [
            r'\b(Grand Cru)\b',
            r'\b(Cru Beaujolais)\b',
            r'\b(\d+(?:er|ème))\s+([A-Z])\b',
            r'\b(\d+(?:er|ème))\b',
            r'\b(2e vin de)\b',
        ]

    def get_cleanup_patterns(self) -> List[str]:
        """Return cleanup patterns - override for parser-specific patterns"""
        return [
            r'\b\d+(?:er|ème)\s+[A-Z]\b',
            r'\b\d+(?:er|ème)\b',
            r'\b(2e vin de)\b',
            r'\b(Grand Cru)\b',
            r'\b(Cru Beaujolais)\b',
            r'\([^)]*\)',
            r'\bigt\b',
            r'\b[A-Z]\s*$',
        ]

    def get_region_mappings(self) -> Dict[str, str]:
        """Return region abbreviation mappings - override for parser-specific mappings"""
        return {}

    # Abstract methods - MUST be implemented by subclasses
    @abstractmethod
    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single line from PDF - specific implementation per parser"""
        pass

    @abstractmethod
    def get_output_path(self) -> str:
        """Return the output path for saving results"""
        pass

    # Main entry point
    def parse_and_save(self, pdf_path: str) -> bool:
        """Parse PDF and save to CSV - main entry point"""
        df = self.parse_pdf_to_dataframe(pdf_path)

        if df.empty:
            print("❌ No data to save")
            return False

        # Save to CSV
        output_path = self.get_output_path()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False, encoding='utf-8')
        print(f"✅ Saved {len(df)} wines to {output_path}")

        # Print statistics
        if self.skipped_lines:
            print(f"⚠️ Skipped {len(self.skipped_lines)} lines")
        if self.error_lines:
            print(f"❌ Error lines: {len(self.error_lines)}")

        return True
