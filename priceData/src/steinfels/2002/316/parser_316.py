#!/usr/bin/env python3
"""
Steinfels Parser 316 (2002) - Refactored
Inherits from BaseSteinfelsParser
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from typing import Dict
from steinfels.2003.320.parser_320 import SteinfelsParser320


class SteinfelsParser316(SteinfelsParser320):
    """Parser for 316.pdf - reuses 320 logic"""

    def get_output_path(self) -> str:
        return '../../validatedOutput/316_wines_parsed.csv'


if __name__ == '__main__':
    parser = SteinfelsParser316()
    pdf_path = '../../../import/steinfels/316.pdf'
    parser.parse_and_save(pdf_path)
