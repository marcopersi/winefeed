#!/usr/bin/env python3
"""Test script to verify unit conversion fix"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser_319 import SteinfelsParser319

def test_unit_conversion():
    parser = SteinfelsParser319()
    
    test_cases = [
        ("6 Flaschen", 7.5),     # Should be 7.5, not 6*7.5=45
        ("12 Flaschen", 7.5),    # Should be 7.5, not 12*7.5=90  
        ("2 Magnum", 15.0),      # Should be 15.0, not 2*15=30
        ("3 Magnum", 15.0),      # Should be 15.0, not 3*15=45
        ("1 Jéroboam", 30.0),    # Should be 30.0, not 1*30=30
        ("24 3/8 Flaschen", 3.75), # Should be 3.75 (3/8 of a liter)
    ]
    
    print("Testing unit conversion fix:")
    print("=" * 50)
    
    for quantity_text, expected in test_cases:
        result = parser.convert_unit_to_deciliters(quantity_text)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{quantity_text}' -> {result} dl (expected: {expected} dl)")
        
        if result != expected:
            print(f"   ERROR: Got {result}, expected {expected}")
    
    print("=" * 50)

if __name__ == "__main__":
    test_unit_conversion()
