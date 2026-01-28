#!/usr/bin/env python3
"""
Steinfels PDF to Excel Converter
Converts Steinfels auction PDFs to Excel format for manual review
Each auction gets its own Excel sheet
"""

import re
import pdfplumber
import pandas as pd
from typing import List, Dict, Optional
from wine_unit_detector import WineUnitDetector
import os
from datetime import datetime

class SteinfelsToExcelConverter:
    def __init__(self):
        """Initialize the converter with unit detector"""
        self.unit_detector = WineUnitDetector()
        
    def extract_auction_date(self, pdf_path: str) -> Optional[str]:
        """Extract auction date from PDF header"""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                first_page = pdf.pages[0]
                text = first_page.extract_text()
                
                # Look for German date patterns
                date_patterns = [
                    r'(\d{1,2})\.\s*(\w+)\s*(\d{4})',  # "12. Mai 2002"
                    r'(\d{1,2})\.(\d{1,2})\.(\d{4})',   # "12.05.2002"
                ]
                
                # German month names
                german_months = {
                    'januar': '01', 'februar': '02', 'märz': '03',
                    'april': '04', 'mai': '05', 'juni': '06',
                    'juli': '07', 'august': '08', 'september': '09',
                    'oktober': '10', 'november': '11', 'dezember': '12'
                }
                
                for pattern in date_patterns:
                    matches = re.finditer(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if len(match.groups()) == 3:
                            day, month_or_num, year = match.groups()
                            
                            # Convert German month name to number
                            if month_or_num.lower() in german_months:
                                month = german_months[month_or_num.lower()]
                            else:
                                month = month_or_num.zfill(2)
                                
                            # Format as ISO date
                            return f"{year}-{month}-{day.zfill(2)}"
                            
        except Exception as e:
            print(f"Error extracting date: {e}")
            
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
                return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def parse_wine_line(self, line: str) -> Optional[Dict]:
        """Parse a single wine line with intelligent unit detection"""
        # Pattern for wine lines with lot number
        wine_pattern = (
            r'^(\d+)\s+'  # Lot number
            r'(.+?)'      # Wine description (non-greedy)
            r'\s+'
            r'(.+?)'      # Year/Vintage and additional info
            r'\s+'
            r'(\d+(?:\'\d+)*)'  # Price with apostrophes
        )
        
        match = re.match(wine_pattern, line.strip())
        if not match:
            return None
            
        lot_number, description, year_info, price_str = match.groups()
        
        # Extract year from year_info
        year_match = re.search(r'\b(19\d{2}|20\d{2})\b', year_info)
        year = year_match.group(1) if year_match else None
        
        # Clean price (remove apostrophes, convert to integer)
        price = int(price_str.replace("'", ""))
        
        # Use intelligent unit detection
        full_text = f"{description} {year_info}"
        quantity, unit_deciliters, unit_description, is_ohk = (
            self.unit_detector.parse_wine_quantity_and_unit(full_text)
        )
        
        # Clean wine name (remove quantity info)
        wine_name = self.clean_wine_name(description)
        
        return {
            'Lot': lot_number,
            'Wine': wine_name,
            'Year': year,
            'Quantity': quantity,
            'Unit': unit_description,
            'Unit_DL': unit_deciliters,
            'OHK': 'Yes' if is_ohk else 'No',
            'Price_CHF': price,
            'Original_Description': description,
            'Year_Info': year_info,
            'Raw_Line': line.strip()
        }

    def clean_wine_name(self, description: str) -> str:
        """Clean wine name by removing quantity indicators"""
        # Remove common quantity patterns
        quantity_patterns = [
            r'\d+\s*(?:flasche|bottle)(?:n)?\s*',
            r'\d+\s*(?:halbe?\s+)?(?:flasche|bottle)(?:n)?\s*',
            r'\d+\s*(?:magnum|doppelmagnum|jeroboam|imperial)(?:s)?\s*',
            r'(?:ohk|oc|original wooden case)\s*',
            r'\d+(?:\.\d+)?\s*[lL]\s*',
        ]
        
        cleaned = description
        for pattern in quantity_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
            
        return cleaned.strip()

    def parse_pdf_to_dataframe(self, pdf_path: str) -> pd.DataFrame:
        """Parse PDF and return DataFrame"""
        print(f"Parsing PDF: {pdf_path}")
        
        # Extract auction date
        auction_date = self.extract_auction_date(pdf_path)
        print(f"Detected auction date: {auction_date}")
        
        # Extract text
        text = self.extract_text_from_pdf(pdf_path)
        if not text:
            print("No text extracted from PDF")
            return pd.DataFrame()
            
        # Parse wine lines
        wines = []
        lines = text.split('\n')
        
        for line in lines:
            # Skip empty lines and headers
            if not line.strip() or len(line.strip()) < 10:
                continue
                
            # Parse wine line
            wine_data = self.parse_wine_line(line)
            if wine_data:
                # Add auction date
                wine_data['Auction_Date'] = auction_date
                wines.append(wine_data)
                
        # Create DataFrame
        df = pd.DataFrame(wines)
        
        # Reorder columns for better readability
        if not df.empty:
            column_order = [
                'Lot', 'Wine', 'Year', 'Quantity', 'Unit', 'Unit_DL', 
                'OHK', 'Price_CHF', 'Auction_Date', 'Original_Description', 
                'Year_Info', 'Raw_Line'
            ]
            df = df[column_order]
            
        return df

    def convert_pdfs_to_excel(self, pdf_files: List[str], 
                            output_file: str = None) -> str:
        """Convert multiple PDFs to Excel with separate sheets"""
        if not output_file:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"steinfels_auction_data_{timestamp}.xlsx"
            
        # Create Excel writer
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            total_wines = 0
            
            for pdf_file in pdf_files:
                if not os.path.exists(pdf_file):
                    print(f"File not found: {pdf_file}")
                    continue
                    
                print(f"\n{'='*60}")
                print(f"Processing: {pdf_file}")
                print(f"{'='*60}")
                
                # Parse PDF to DataFrame
                df = self.parse_pdf_to_dataframe(pdf_file)
                
                if df.empty:
                    print(f"No wines found in {pdf_file}")
                    continue
                    
                # Create sheet name from filename
                sheet_name = os.path.basename(pdf_file).replace('.pdf', '')
                if len(sheet_name) > 31:  # Excel sheet name limit
                    sheet_name = sheet_name[:31]
                    
                # Write to Excel sheet
                df.to_excel(writer, sheet_name=sheet_name, index=False)
                
                # Auto-adjust column widths
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
                
                total_wines += len(df)
                print(f"✓ Added {len(df)} wines to sheet '{sheet_name}'")
                
                # Show sample of first few wines
                print("\nSample wines:")
                for i, row in df.head(3).iterrows():
                    ohk_indicator = " [OHK]" if row['OHK'] == 'Yes' else ""
                    print(f"  Lot {row['Lot']}: {row['Wine']} ({row['Year']}) "
                          f"- {row['Quantity']}x {row['Unit']}{ohk_indicator}")
                          
        print(f"\n🎉 TOTAL: {total_wines} wines exported to {output_file}")
        print(f"📊 You can now review and validate the data manually!")
        return output_file

def main():
    """Main function to convert Steinfels PDFs to Excel"""
    converter = SteinfelsToExcelConverter()
    
    # Convert 2002 PDFs
    pdf_files_2002 = [
        "import/steinfels/2002/315.pdf",
        "import/steinfels/2002/316.pdf", 
        "import/steinfels/2002/317.pdf",
        "import/steinfels/2002/318.pdf",
        "import/steinfels/2002/319.pdf"
    ]
    
    # Convert 2003 PDFs  
    pdf_files_2003 = [
        "import/steinfels/2003/320.pdf",
        "import/steinfels/2003/321.pdf",
        "import/steinfels/2003/322.pdf", 
        "import/steinfels/2003/323.pdf",
        "import/steinfels/2003/324.pdf"
    ]
    
    # Convert 2002 auctions
    print("Converting 2002 Steinfels Auctions...")
    output_2002 = converter.convert_pdfs_to_excel(
        pdf_files_2002, 
        "steinfels_2002_auctions.xlsx"
    )
    
    # Convert 2003 auctions
    print("\n" + "="*80)
    print("Converting 2003 Steinfels Auctions...")
    output_2003 = converter.convert_pdfs_to_excel(
        pdf_files_2003,
        "steinfels_2003_auctions.xlsx" 
    )
    
    print(f"\n🎯 CONVERSION COMPLETE!")
    print(f"📁 2002 Auctions: {output_2002}")
    print(f"📁 2003 Auctions: {output_2003}")
    print(f"\n💡 Next steps:")
    print(f"   1. Open Excel files and review data")
    print(f"   2. Manually correct any parsing errors")
    print(f"   3. Run Excel import script to load into database")

if __name__ == "__main__":
    main()
