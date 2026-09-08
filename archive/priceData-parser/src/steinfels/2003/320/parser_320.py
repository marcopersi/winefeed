#!/usr/bin/env python3
"""
Steinfels Parser 320 (2003) - Refactored
Inherits from BaseSteinfelsParser - implements only parser-specific logic
"""

import re
import sys
import os
from typing import Optional, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from base_parser import BaseSteinfelsParser


class SteinfelsParser320(BaseSteinfelsParser):
    """Parser for 320.pdf - implements only parse_line method"""

    def get_wine_regions(self) -> List[str]:
        """Extended regions for parser 320"""
        regions = super().get_wine_regions()
        # Add 320-specific regions
        regions.extend([
            'Haut-Mé', 'Pauill', 'St-Em', 'St-Jul', 'Pessac-Léo',
        ])
        return regions

    def get_region_mappings(self) -> Dict[str, str]:
        """Region abbreviation mappings for parser 320"""
        return {
            'Haut-Mé': 'Haut-Médoc',
            'Pauill': 'Pauillac',
            'St-Em': 'Saint-Emilion',
            'St-Jul': 'Saint-Julien',
            'Pessac-Léo': 'Pessac-Léognan',
            'Saint-Emilio': 'Saint-Emilion',
        }

    def get_wine_producers(self) -> List[str]:
        """Extended producers for parser 320"""
        producers = super().get_wine_producers()
        # Add 320-specific producers
        producers.extend([
            'Collection Dr. Barolet', 'Bouchard Âiné & Fils', 'Paul Bouchard & Cie',
            'Bouchard Père & Fils', 'Bouchard Père & Fil', 'Paul Bouchard & Ci',
            'J. Hubert-Didier', 'Michel Noëllat', 'Drouhin-Laroze', 'G. de Buyssières',
            'Etienne Sauzet', 'Jean-Marie Garnier', 'Taittinger',
            'Angelo Gaja', 'Carlo Boffa', 'Sottimano', 'Conterno Fantino',
            'Luciano Sandro', 'Scavino', 'Castello dei Rampolla', 'Dominus Estate',
            'Louis Latour', 'Comte Georges', 'Produttori del Barbaresco'
        ])
        return producers

    def get_classification_patterns(self) -> List[str]:
        """Extended classification patterns for parser 320"""
        return [
            r'\b(Grand\s+Cru\s+Classé)\b',
            r'\b(Grand\s+Cru)\b',
            r'\b(Cru\s+Classé)\b',
            r'\b(Cru\s+Beaujolais)\b',
            r'\b(Cru\s+Bourgeois)\b',
            r'\b(\d+(?:er|ème)\s+Cru\s+Classé)\b',
            r'\b(\d+(?:er|ème)\s+Cru)\b',
            r'\b(\d+(?:er|ème))\s+(Cru\s+[AB])\b',
            r'\b(\d+(?:er|ème))\s+([AB])\b',
            r'\b(\d+(?:er|ème))\b',
            r'\b(2e\s+vin\s+de)\b',
        ]

    def get_cleanup_patterns(self) -> List[str]:
        """Extended cleanup patterns for parser 320"""
        return [
            r'\b\d+(?:er|ème)\s+Cru\s+[AB]\b',
            r'\b\d+(?:er|ème)\s+Cru\b',
            r'\b(Cru\s+[AB])\b',
            r'\bCru\b',
            r'\b\d+(?:er|ème)\s+[AB]\b',
            r'\b\d+(?:er|ème)\b',
            r'\b(2e vin de)\b',
            r'\b(Grand Cru)\b',
            r'\b(Cru Beaujolais)\b',
            r'\b(Cru Bourgeois)\b',
            r'\([^)]*\)',
            r'\bigt\b',
            r'\b[A-Z]\s*$',
        ]

    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single line - specific implementation for parser 320"""
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

        # Extract quantity and unit (supports fractions like "24 3/8 Flaschen")
        unit_match = re.search(
            r'(\d+(?:\s+\d+/\d+)?)\s+(Flasche|Flaschen|Magnum|Doppelmagnum|Jéroboam)\s*$',
            remaining_line, re.IGNORECASE)
        if not unit_match:
            self.error_lines.append(f"NO_UNIT: {line}")
            return None

        quantity_str = unit_match.group(1)
        unit = unit_match.group(2)
        
        # Parse quantity (handle fractions)
        if '/' in quantity_str:
            # e.g. "24 3/8" -> quantity=24
            quantity = int(quantity_str.split()[0])
        else:
            quantity = int(quantity_str)
        
        remaining_line = remaining_line[:unit_match.start()].strip()

        # Now remaining_line contains: Wine Name + Producer + Region + Classification
        # First extract classification
        after_classification_extraction, classification = self.extract_classification(remaining_line)

        # Then clean the text
        cleaned_line = self.clean_text(after_classification_extraction)

        # Extract region
        after_region_extraction, region = self.extract_region(cleaned_line)

        # Extract producer
        after_producer_extraction, producer = self.extract_producer(after_region_extraction)

        # What's left should be the wine name
        wine_name = after_producer_extraction.strip()

        # Convert unit to deciliters (handle fractions)
        unit_dl = self.convert_unit_to_deciliters_with_fraction(quantity_str, unit)

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
            'Raw_Line': line.strip(),
        }

    def convert_unit_to_deciliters_with_fraction(self, quantity_str: str, unit: str) -> float:
        """Convert unit string to deciliters - handles fractions like "24 3/8" """
        # Check for fraction pattern like "24 3/8"
        fraction_match = re.search(r'(\d+)\s+(\d+)/(\d+)', quantity_str)
        if fraction_match:
            numerator = int(fraction_match.group(2))
            denominator = int(fraction_match.group(3))
            # Calculate fraction size: 3/8 = 0.375L = 3.75dl
            return (numerator / denominator) * 10

        # Standard unit conversion
        unit_lower = unit.lower()
        if unit_lower in ['flasche', 'flaschen']:
            return 7.5  # Standard bottle
        elif unit_lower == 'magnum':
            return 15.0  # Magnum
        elif unit_lower in ['doppelmagnum', 'jéroboam']:
            return 30.0  # Double Magnum
        else:
            return 7.5  # Default

    def get_output_path(self) -> str:
        """Return the output path for saving results"""
        return '../../validatedOutput/320_wines_parsed.csv'


if __name__ == '__main__':
    parser = SteinfelsParser320()
    pdf_path = '../../../import/steinfels/320.pdf'
    parser.parse_and_save(pdf_path)
