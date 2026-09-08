#!/usr/bin/env python3
"""
Analyze the 315.pdf to understand the structure better
"""

import pdfplumber
import re

def analyze_315_pdf():
    pdf_path = "import/steinfels/2002/315.pdf"
    
    with pdfplumber.open(pdf_path) as pdf:
        print(f"Total pages: {len(pdf.pages)}")
        
        # Extract first page text
        first_page = pdf.pages[0]
        text = first_page.extract_text()
        
        print("\n" + "="*80)
        print("FIRST PAGE TEXT:")
        print("="*80)
        print(text)
        
        # Look for the first few wine lines
        lines = text.split('\n')
        print("\n" + "="*80)
        print("FIRST 20 LINES:")
        print("="*80)
        
        for i, line in enumerate(lines[:20]):
            if line.strip():
                print(f"{i+1:2d}: {line}")
                
        # Look for lines that start with numbers (lot numbers)
        print("\n" + "="*80)
        print("LINES STARTING WITH NUMBERS (first 10):")
        print("="*80)
        
        lot_lines = []
        for line in lines:
            if re.match(r'^\d+\s+', line.strip()):
                lot_lines.append(line.strip())
                
        for i, line in enumerate(lot_lines[:10]):
            print(f"{i+1:2d}: {line}")

if __name__ == "__main__":
    analyze_315_pdf()
