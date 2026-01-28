#!/usr/bin/env python3
"""
Steinfels Parser 315 (2002) - Refactored
Inherits from BaseSteinfelsParser - implements only parser-specific logic
"""

import re
import sys
import os
from typing import Optional, Dict

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from base_parser import BaseSteinfelsParser


class SteinfelsParser315(BaseSteinfelsParser):
    """Parser for 315.pdf - implements only parse_line method"""

    def parse_line(self, line: str) -> Optional[Dict]:
        """Parse a single line - specific implementation for parser 315"""
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
        unit_dl = self.convert_unit_to_deciliters_custom(unit)

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
            'Original_Line': remaining_line,
            'After_Classification': after_classification_extraction,
            'Cleaned_Line': cleaned_line,
        }

    def convert_unit_to_deciliters_custom(self, unit: str) -> float:
        """Convert unit string to deciliters - custom for parser 315"""
        unit_lower = unit.lower()
        if unit_lower in ['flasche', 'flaschen']:
            return 7.5  # Standard bottle
        elif unit_lower == 'magnum':
            return 15.0  # Magnum
        elif unit_lower == 'doppelmagnum':
            return 30.0  # Double Magnum
        else:
            return 7.5  # Default to standard bottle

    def get_output_path(self) -> str:
        """Return the output path for saving results"""
        return '../../validatedOutput/315_wines_enhanced.csv'


if __name__ == '__main__':
    parser = SteinfelsParser315()
    pdf_path = '../../../import/steinfels/315.pdf'
    parser.parse_and_save(pdf_path)
