#!/usr/bin/env python3
"""
Intelligent Wine Unit Detection Utility
Detects wine bottle sizes and units from text descriptions
"""

import re
from typing import Tuple, Optional


class WineUnitDetector:
    """Intelligently detects wine bottle units from text"""
    
    def __init__(self):
        # Unit mappings: (pattern, deciliters, description)
        self.unit_patterns = [
            # Specific volume mentions (check first for precision)
            (r'(\d+(?:\.\d+)?)\s*[lL]', None, 'Volume in liters'),
            (r'(\d+)\s*cl', 0.1, 'Volume in centiliters'),
            (r'(\d+)\s*ml', 0.01, 'Volume in milliliters'),
            
            # Half bottles (check before standard bottles)
            (r'halbe\s+(?:flasche|bottle)(?:n)?', 3.75, 'Half bottle'),
            (r'(?:flasche|bottle)(?:n)?\s+(?:0\.375|3\.75)', 3.75,
             'Half bottle'),
            
            # Large format bottles (check before magnum for doppel)
            (r'(?:doppel\s*magnum|double\s+magnum)(?:s)?', 30.0,
             'Double Magnum'),
            (r'jeroboam(?:s)?', 45.0, 'Jeroboam (4.5L)'),
            (r'(?:4\.5\s*[lL])|(?:4,5\s*[lL])', 45.0, 'Jeroboam (4.5L)'),
            (r'imperial(?:s)?', 60.0, 'Imperial (6L)'),
            (r'(?:6\.0?\s*[lL])|(?:6,0?\s*[lL])', 60.0, 'Imperial (6L)'),
            (r'salmanazar(?:s)?', 90.0, 'Salmanazar (9L)'),
            (r'(?:9\.0?\s*[lL])|(?:9,0?\s*[lL])', 90.0, 'Salmanazar (9L)'),
            (r'balthazar(?:s)?', 120.0, 'Balthazar (12L)'),
            (r'(?:12\.0?\s*[lL])|(?:12,0?\s*[lL])', 120.0, 'Balthazar (12L)'),
            (r'nebuchadnezzar(?:s)?', 150.0, 'Nebuchadnezzar (15L)'),
            (r'(?:15\.0?\s*[lL])|(?:15,0?\s*[lL])', 150.0,
             'Nebuchadnezzar (15L)'),
            (r'melchior(?:s)?', 180.0, 'Melchior (18L)'),
            (r'(?:18\.0?\s*[lL])|(?:18,0?\s*[lL])', 180.0, 'Melchior (18L)'),
            
            # Standard magnum and bottles (after doppelmagnum)
            (r'(?:1\s+)?magnum(?:s)?', 15.0, 'Magnum'),
            (r'(?:normale?\s+)?(?:flasche|bottle)(?:n)?', 7.5,
             'Standard bottle'),
        ]
        
        # OHK/OC patterns
        self.ohk_patterns = [
            r'\bOHK\b',
            r'\bO\.H\.K\.?\b',
            r'\bOC\b',
            r'\bO\.C\.?\b',
            r'original\s+(?:wooden\s+)?(?:case|carton|box)',
            r'original\s+holz\s*kiste',
            r'original\s+karton',
            r'originale?\s+(?:kiste|karton)',
        ]
    
    def extract_quantity(self, text: str) -> int:
        """Extract the number of bottles/units from text"""
        text = text.lower().strip()
        
        # Look for explicit numbers at the start
        quantity_match = re.search(r'^(\d+)\s+', text)
        if quantity_match:
            return int(quantity_match.group(1))
        
        # Look for numbers before bottle/flasche
        quantity_match = re.search(r'(\d+)\s+(?:flaschen?|bottles?)', text)
        if quantity_match:
            return int(quantity_match.group(1))
        
        # Special cases for fractions
        if re.search(r'(?:halbe?|1/2|0\.5)', text):
            return 1  # Half bottle is still 1 unit
        
        # Default to 1 bottle
        return 1
    
    def detect_unit(self, text: str) -> Tuple[float, str]:
        """
        Detect wine unit from text description
        Returns: (deciliters, description)
        """
        text_lower = text.lower()
        
        # Check each pattern
        for pattern, base_deciliters, description in self.unit_patterns:
            match = re.search(pattern, text_lower)
            if match:
                if base_deciliters is None:
                    # Volume in liters pattern - extract the number
                    volume_liters = float(match.group(1))
                    deciliters = volume_liters * 10
                    return deciliters, f"{volume_liters}L bottle"
                else:
                    return base_deciliters, description
        
        # Default to standard bottle if nothing found
        return 7.5, "Standard bottle (assumed)"
    
    def detect_ohk(self, text: str) -> bool:
        """Detect if the offering includes original wooden case/carton"""
        text_lower = text.lower()
        
        for pattern in self.ohk_patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return True
        
        return False
    
    def parse_wine_quantity_and_unit(self, text: str):
        """
        Parse wine quantity and unit from text.
        Returns: (quantity, deciliters, description, is_ohk)
        """
        """
        Parse complete wine quantity and unit information
        Returns: (quantity, unit_deciliters, unit_description, is_ohk)
        """
        quantity = self.extract_quantity(text)
        unit_deciliters, unit_description = self.detect_unit(text)
        is_ohk = self.detect_ohk(text)
        
        return quantity, unit_deciliters, unit_description, is_ohk


def test_unit_detector():
    """Test the unit detector with various inputs"""
    detector = WineUnitDetector()
    
    test_cases = [
        "12 Flaschen OHK",
        "6 Magnum",
        "1 Doppelmagnum",
        "3 Flaschen 4.5L",
        "24 halbe Flaschen",
        "1 Imperial 6L",
        "12 Flaschen OC",
        "6 Flaschen original wooden case",
        "18 Flaschen",
        "1 Jeroboam 4.5L OHK",
        "2 Balthazar 12L",
        "1 Magnum 1967",
        "23 Flaschen 1966",
    ]
    
    print("🧪 TESTING WINE UNIT DETECTOR")
    print("=" * 60)
    
    for test_text in test_cases:
        quantity, deciliters, description, is_ohk = detector.parse_wine_quantity_and_unit(test_text)
        ohk_indicator = " [OHK]" if is_ohk else ""
        print(f"{test_text:30} → {quantity}x {description} ({deciliters}dl){ohk_indicator}")


if __name__ == "__main__":
    test_unit_detector()
