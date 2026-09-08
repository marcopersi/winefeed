"""
Excel Data Import Script for vinoStagingFile2015-2008.xlsx
Maps Excel wine data to the Supabase wine domain model
"""

import pandas as pd
import numpy as np
from datetime import datetime, date
from supabase_config import SupabaseConfig
from typing import Dict, List, Optional, Any
import re


class VinoExcelImporter:
    """Import wine data from Excel file to Supabase database"""
    
    def __init__(self, excel_file_path: str):
        self.excel_file_path = excel_file_path
        self.config = SupabaseConfig()
        self.client = self.config.get_client()
        self.df = None
        
        # Cache for database entities to avoid duplicates
        self.wine_cache = {}
        self.provider_cache = {}
        self.agency_cache = {}
        self.unit_cache = {}
        
    def load_excel_data(self):
        """Load and analyze the Excel file"""
        print(f"Loading Excel file: {self.excel_file_path}")
        
        try:
            # Try to read the Excel file
            self.df = pd.read_excel(self.excel_file_path)
            print(f"✓ Successfully loaded {len(self.df)} rows")
            print(f"✓ Columns found: {list(self.df.columns)}")
            
            # Show first few rows for analysis
            print("\n=== First 5 rows for analysis ===")
            print(self.df.head())
            
            # Show data types
            print("\n=== Data types ===")
            print(self.df.dtypes)
            
            # Show basic statistics
            print("\n=== Basic statistics ===")
            print(self.df.describe(include='all'))
            
            return True
            
        except Exception as e:
            print(f"❌ Error loading Excel file: {e}")
            return False
    
    def analyze_columns(self):
        """Analyze columns to understand the data structure"""
        if self.df is None:
            print("❌ No data loaded. Call load_excel_data() first.")
            return
        
        print("\n=== Column Analysis ===")
        for col in self.df.columns:
            print(f"\nColumn: {col}")
            print(f"  Type: {self.df[col].dtype}")
            print(f"  Non-null: {self.df[col].count()}/{len(self.df)}")
            print(f"  Unique values: {self.df[col].nunique()}")
            
            # Show some sample values
            sample_values = self.df[col].dropna().unique()[:5]
            print(f"  Sample values: {sample_values}")
            
            # Check for potential wine names, producers, etc.
            if 'name' in col.lower() or 'wine' in col.lower():
                print(f"  → Potential WINE NAME column")
            elif 'producer' in col.lower() or 'winery' in col.lower() or 'estate' in col.lower():
                print(f"  → Potential PRODUCER column")
            elif 'year' in col.lower() or 'vintage' in col.lower():
                print(f"  → Potential VINTAGE column")
            elif 'region' in col.lower() or 'appellation' in col.lower():
                print(f"  → Potential REGION column")
            elif 'price' in col.lower() or 'cost' in col.lower() or 'value' in col.lower():
                print(f"  → Potential PRICE column")
            elif 'rating' in col.lower() or 'score' in col.lower() or 'points' in col.lower():
                print(f"  → Potential RATING column")
            elif 'date' in col.lower():
                print(f"  → Potential DATE column")
    
    def map_columns_to_schema(self):
        """Interactive mapping of Excel columns to database schema"""
        if self.df is None:
            print("❌ No data loaded. Call load_excel_data() first.")
            return None
        
        print("\n=== Mapping Columns to Wine Domain Schema ===")
        
        # Define the expected mappings
        column_mappings = {}
        
        # Wine table fields
        wine_fields = ['name', 'producer', 'vintage', 'region', 'origin']
        
        # Try to auto-detect column mappings
        for field in wine_fields:
            best_match = self._find_best_column_match(field)
            if best_match:
                column_mappings[field] = best_match
                print(f"✓ Auto-mapped '{field}' → '{best_match}'")
        
        # Look for price/offering related columns
        price_fields = ['price', 'pricemin', 'pricemax', 'realizedprice']
        for field in price_fields:
            best_match = self._find_best_column_match(field)
            if best_match:
                column_mappings[field] = best_match
                print(f"✓ Auto-mapped '{field}' → '{best_match}'")
        
        # Look for rating related columns
        rating_fields = ['rating', 'score', 'points']
        for field in rating_fields:
            best_match = self._find_best_column_match(field)
            if best_match:
                column_mappings[field] = best_match
                print(f"✓ Auto-mapped '{field}' → '{best_match}'")
        
        # Look for date columns
        date_fields = ['date', 'offeringdate', 'vintage']
        for field in date_fields:
            best_match = self._find_best_column_match(field)
            if best_match:
                column_mappings[field] = best_match
                print(f"✓ Auto-mapped '{field}' → '{best_match}'")
        
        return column_mappings
    
    def _find_best_column_match(self, field: str) -> Optional[str]:
        """Find the best matching column for a field"""
        field_lower = field.lower()
        
        # Direct matches
        for col in self.df.columns:
            col_lower = col.lower()
            if field_lower == col_lower:
                return col
        
        # Partial matches
        for col in self.df.columns:
            col_lower = col.lower()
            if field_lower in col_lower or col_lower in field_lower:
                return col
        
        # Special mappings
        mappings = {
            'name': ['wine', 'title', 'label', 'cuvee'],
            'producer': ['winery', 'estate', 'chateau', 'domaine', 'maker'],
            'vintage': ['year', 'jahrgang'],
            'region': ['appellation', 'ava', 'zone', 'area'],
            'origin': ['country', 'nation', 'land'],
            'price': ['cost', 'value', 'amount'],
            'pricemin': ['min_price', 'minimum', 'estimate_low'],
            'pricemax': ['max_price', 'maximum', 'estimate_high'],
            'realizedprice': ['realized', 'final_price', 'sold_price', 'hammer'],
            'rating': ['score', 'points', 'note'],
            'date': ['datum', 'when', 'time']
        }
        
        if field in mappings:
            for col in self.df.columns:
                col_lower = col.lower()
                for keyword in mappings[field]:
                    if keyword in col_lower:
                        return col
        
        return None
    
    def preview_import(self, column_mappings: Dict[str, str], max_rows: int = 5):
        """Preview how the data would be imported"""
        if self.df is None:
            print("❌ No data loaded.")
            return
        
        print(f"\n=== Preview Import (first {max_rows} rows) ===")
        
        for i, (idx, row) in enumerate(self.df.head(max_rows).iterrows()):
            print(f"\n--- Row {i+1} ---")
            
            # Wine data
            wine_data = {}
            for field, col in column_mappings.items():
                if field in ['name', 'producer', 'vintage', 'region', 'origin'] and col in self.df.columns:
                    value = row[col]
                    if pd.notna(value):
                        wine_data[field] = value
            print(f"Wine: {wine_data}")
            
            # Price/offering data
            offering_data = {}
            for field, col in column_mappings.items():
                if field in ['price', 'pricemin', 'pricemax', 'realizedprice'] and col in self.df.columns:
                    value = row[col]
                    if pd.notna(value):
                        offering_data[field] = value
            if offering_data:
                print(f"Offering: {offering_data}")
            
            # Rating data
            rating_data = {}
            for field, col in column_mappings.items():
                if field in ['rating', 'score', 'points'] and col in self.df.columns:
                    value = row[col]
                    if pd.notna(value):
                        rating_data[field] = value
            if rating_data:
                print(f"Rating: {rating_data}")
    
    def import_data(self, column_mappings: Dict[str, str], dry_run: bool = True):
        """Import the Excel data to Supabase"""
        if self.df is None:
            print("❌ No data loaded.")
            return False
        
        print(f"\n=== {'DRY RUN: ' if dry_run else ''}Importing {len(self.df)} rows ===")
        
        # Load existing cache data
        self._load_caches()
        
        imported_wines = 0
        imported_ratings = 0
        imported_offerings = 0
        errors = []
        
        for idx, row in self.df.iterrows():
            try:
                # Extract wine data
                wine_data = self._extract_wine_data(row, column_mappings)
                if not wine_data:
                    continue
                
                print(f"Processing row {idx + 1}: {wine_data.get('name', 'Unknown')} {wine_data.get('vintage', '')}")
                
                # Get or create wine
                wine_id = self._get_or_create_wine(wine_data, dry_run)
                if wine_id:
                    imported_wines += 1
                
                # Extract and create rating if present
                rating_data = self._extract_rating_data(row, column_mappings)
                if rating_data and wine_id:
                    rating_id = self._create_rating(wine_id, rating_data, dry_run)
                    if rating_id:
                        imported_ratings += 1
                
                # Extract and create offering if present
                offering_data = self._extract_offering_data(row, column_mappings)
                if offering_data and wine_id:
                    offering_id = self._create_offering_and_link(wine_id, offering_data, dry_run)
                    if offering_id:
                        imported_offerings += 1
                
            except Exception as e:
                error_msg = f"Row {idx + 1}: {str(e)}"
                errors.append(error_msg)
                print(f"❌ {error_msg}")
        
        # Summary
        print(f"\n=== Import Summary ===")
        print(f"{'DRY RUN - ' if dry_run else ''}Wines: {imported_wines}")
        print(f"{'DRY RUN - ' if dry_run else ''}Ratings: {imported_ratings}")
        print(f"{'DRY RUN - ' if dry_run else ''}Offerings: {imported_offerings}")
        print(f"Errors: {len(errors)}")
        
        if errors:
            print("\n=== Errors ===")
            for error in errors[:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(errors) > 10:
                print(f"  ... and {len(errors) - 10} more errors")
        
        return len(errors) == 0
    
    def _load_caches(self):
        """Load existing database entities to avoid duplicates"""
        # Load existing rating agencies
        agencies = self.client.table('ratingagency').select('*').execute()
        for agency in agencies.data:
            self.agency_cache[agency['ratingagencyname'].lower()] = agency['id']
        
        # Load existing units
        units = self.client.table('unit').select('*').execute()
        for unit in units.data:
            self.unit_cache[float(unit['deciliters'])] = unit['id']
    
    def _extract_wine_data(self, row, mappings: Dict[str, str]) -> Dict[str, Any]:
        """Extract wine data from a row"""
        wine_data = {}
        
        for field in ['name', 'producer', 'vintage', 'region', 'origin']:
            if field in mappings and mappings[field] in row:
                value = row[mappings[field]]
                if pd.notna(value):
                    wine_data[field] = str(value).strip()
        
        # Ensure we have at least a name
        return wine_data if wine_data.get('name') else None
    
    def _extract_rating_data(self, row, mappings: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract rating data from a row"""
        rating_data = {}
        
        # Look for rating/score
        for field in ['rating', 'score', 'points']:
            if field in mappings and mappings[field] in row:
                value = row[mappings[field]]
                if pd.notna(value) and value != '':
                    try:
                        rating_data['score'] = float(value)
                        break
                    except:
                        continue
        
        return rating_data if 'score' in rating_data else None
    
    def _extract_offering_data(self, row, mappings: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """Extract offering/price data from a row"""
        offering_data = {}
        
        # Look for various price fields
        price_fields = ['price', 'pricemin', 'pricemax', 'realizedprice']
        for field in price_fields:
            if field in mappings and mappings[field] in row:
                value = row[mappings[field]]
                if pd.notna(value) and value != '':
                    try:
                        offering_data[field] = float(value)
                    except:
                        continue
        
        # Look for date
        if 'date' in mappings and mappings['date'] in row:
            value = row[mappings['date']]
            if pd.notna(value):
                try:
                    if isinstance(value, str):
                        # Try to parse date string
                        offering_data['offeringdate'] = pd.to_datetime(value).date().isoformat()
                    else:
                        offering_data['offeringdate'] = value.date().isoformat()
                except:
                    pass
        
        return offering_data if offering_data else None
    
    def _get_or_create_wine(self, wine_data: Dict[str, Any], dry_run: bool) -> Optional[int]:
        """Get existing wine or create new one"""
        # Create a cache key
        cache_key = f"{wine_data.get('name', '')}-{wine_data.get('producer', '')}-{wine_data.get('vintage', '')}"
        
        if cache_key in self.wine_cache:
            return self.wine_cache[cache_key]
        
        if dry_run:
            # Simulate wine creation
            self.wine_cache[cache_key] = len(self.wine_cache) + 1000
            return self.wine_cache[cache_key]
        
        # Check if wine exists
        query = self.client.table('wine').select('id')
        if 'name' in wine_data:
            query = query.eq('name', wine_data['name'])
        if 'producer' in wine_data:
            query = query.eq('producer', wine_data['producer'])
        if 'vintage' in wine_data:
            query = query.eq('vintage', wine_data['vintage'])
        
        existing = query.execute()
        if existing.data:
            wine_id = existing.data[0]['id']
            self.wine_cache[cache_key] = wine_id
            return wine_id
        
        # Create new wine
        result = self.client.table('wine').insert(wine_data).execute()
        if result.data:
            wine_id = result.data[0]['id']
            self.wine_cache[cache_key] = wine_id
            return wine_id
        
        return None
    
    def _create_rating(self, wine_id: int, rating_data: Dict[str, Any], dry_run: bool) -> Optional[int]:
        """Create a rating for a wine"""
        if dry_run:
            return len(self.wine_cache) + 2000
        
        # For now, create rating without specific agency
        # In a real scenario, you'd need to map rating sources to agencies
        rating_data['wine_id'] = wine_id
        
        result = self.client.table('rating').insert(rating_data).execute()
        return result.data[0]['id'] if result.data else None
    
    def _create_offering_and_link(self, wine_id: int, offering_data: Dict[str, Any], dry_run: bool) -> Optional[int]:
        """Create an offering and link it to a wine"""
        if dry_run:
            return len(self.wine_cache) + 3000
        
        # Create Wermuth SA provider if not specified (Excel data is from Wermuth SA auction)
        if 'provider_id' not in offering_data:
            provider_name = "Wermuth SA"
            if provider_name not in self.provider_cache:
                # Try to find existing Wermuth SA provider
                existing_provider = self.client.table('provider').select('*').eq('name', provider_name).execute()
                if existing_provider.data:
                    self.provider_cache[provider_name] = existing_provider.data[0]['id']
                else:
                    # Create if doesn't exist
                    provider_result = self.client.table('provider').insert({'name': provider_name}).execute()
                    if provider_result.data:
                        self.provider_cache[provider_name] = provider_result.data[0]['id']
            offering_data['provider_id'] = self.provider_cache.get(provider_name)
        
        # Set providerofferingid if not present
        if 'providerofferingid' not in offering_data:
            offering_data['providerofferingid'] = f"EXCEL-{wine_id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create offering
        result = self.client.table('offering').insert(offering_data).execute()
        if not result.data:
            return None
        
        offering_id = result.data[0]['id']
        
        # Link wine to offering with standard bottle size
        standard_bottle_id = self.unit_cache.get(7.5)  # 750ml
        if standard_bottle_id:
            wine_offering_data = {
                'wine_id': wine_id,
                'offering_id': offering_id,
                'wineunit_id': standard_bottle_id
            }
            self.client.table('wineoffering').insert(wine_offering_data).execute()
        
        return offering_id


def main():
    """Main function to run the Excel import"""
    excel_file = "/Users/marcopersi/development/winefeed/priceData/vinoStagingFile2015-2008.xlsx"
    
    # Initialize importer
    importer = VinoExcelImporter(excel_file)
    
    # Load and analyze the data
    if not importer.load_excel_data():
        return
    
    # Analyze columns
    importer.analyze_columns()
    
    # Map columns to schema
    mappings = importer.map_columns_to_schema()
    if not mappings:
        print("❌ No column mappings found")
        return
    
    print(f"\n=== Final Column Mappings ===")
    for field, col in mappings.items():
        print(f"  {field} → {col}")
    
    # Preview import
    importer.preview_import(mappings)
    
    # Run dry import first
    print("\n" + "="*50)
    print("RUNNING DRY RUN IMPORT")
    print("="*50)
    importer.import_data(mappings, dry_run=True)


if __name__ == "__main__":
    main()
