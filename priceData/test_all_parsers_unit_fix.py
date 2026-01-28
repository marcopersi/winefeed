#!/usr/bin/env python3
"""Test script to verify unit conversion fix across parsers"""

import sys
import os

def test_parser_unit_conversion(parser_number):
    sys.path.append(f'/Users/marcopersi/development/winefeed/priceData/src/steinfels/2002/{parser_number}')
    
    if parser_number == '316':
        from parser_316 import SteinfelsParser316
        parser = SteinfelsParser316()
        
        test_cases = [
            ("Flasche", None, 7.5),
            ("Magnum", None, 15.0),
            ("Flaschen", "24 3/8", 3.75),  # 3/8 of 7.5 = 2.8125, but should be 3.75 (3/8 * 10)
            ("Flaschen", "3/8", 2.8125),   # 3/8 of 7.5 = 2.8125
        ]
        
        print(f"Testing Parser {parser_number} unit conversion:")
        print("=" * 50)
        
        for unit, quantity_str, expected in test_cases:
            result = parser.convert_unit_to_deciliters(unit, quantity_str)
            status = "✓" if abs(result - expected) < 0.01 else "✗"
            print(f"{status} {unit} ({quantity_str}) -> {result} dl (expected: {expected} dl)")
            
    elif parser_number == '318':
        from parser_318 import SteinfelsParser318
        parser = SteinfelsParser318()
        
        test_cases = [
            ("6 Flaschen", 7.5),
            ("12 Flaschen", 7.5),
            ("2 Magnum", 15.0),
            ("1 Jéroboam", 30.0),
        ]
        
        print(f"Testing Parser {parser_number} unit conversion:")
        print("=" * 50)
        
        for quantity_text, expected in test_cases:
            result = parser.convert_unit_to_deciliters(quantity_text)
            status = "✓" if result == expected else "✗"
            print(f"{status} '{quantity_text}' -> {result} dl (expected: {expected} dl)")

if __name__ == "__main__":
    for parser_num in ['316', '318']:
        test_parser_unit_conversion(parser_num)
        print()
