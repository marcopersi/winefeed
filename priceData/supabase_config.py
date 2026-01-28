"""
Supabase Client Configuration
"""
import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SupabaseConfig:
    """Configuration class for Supabase client"""
    
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL", "http://localhost:54321")
        self.anon_key = os.getenv("SUPABASE_ANON_KEY")
        self.service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        
    def get_client(self, use_service_role: bool = False) -> Client:
        """
        Create and return a Supabase client
        
        Args:
            use_service_role: If True, uses service role key for admin operations
            
        Returns:
            Configured Supabase client
        """
        key = self.service_role_key if use_service_role else self.anon_key
        
        if not key:
            raise ValueError(
                f"Missing Supabase key. Please set "
                f"{'SUPABASE_SERVICE_ROLE_KEY' if use_service_role else 'SUPABASE_ANON_KEY'} "
                f"in your .env file"
            )
        
        return create_client(self.url, key)

# Global instance
supabase_config = SupabaseConfig()

# Convenience function to get client
def get_supabase_client(use_service_role: bool = False) -> Client:
    """Get configured Supabase client"""
    return supabase_config.get_client(use_service_role)

# Example usage functions
def test_connection() -> bool:
    """Test the Supabase connection"""
    try:
        supabase = get_supabase_client()
        # Simple test query - this will work even without tables
        response = supabase.rpc('version').execute()
        print("✅ Supabase connection successful!")
        return True
    except Exception as e:
        print(f"❌ Supabase connection failed: {e}")
        return False

def create_wine_table():
    """Example function to create a wine data table"""
    try:
        supabase = get_supabase_client(use_service_role=True)
        
        # Example SQL to create a wine table
        sql = """
        CREATE TABLE IF NOT EXISTS wines (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            producer VARCHAR(255),
            vintage INTEGER,
            region VARCHAR(255),
            price DECIMAL(10,2),
            rating DECIMAL(3,1),
            description TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
        );
        
        -- Enable Row Level Security
        ALTER TABLE wines ENABLE ROW LEVEL SECURITY;
        
        -- Create a policy that allows all operations for now
        CREATE POLICY "Allow all operations" ON wines FOR ALL USING (true);
        """
        
        supabase.rpc('exec_sql', {'sql': sql}).execute()
        print("✅ Wine table created successfully!")
        
    except Exception as e:
        print(f"❌ Failed to create wine table: {e}")

if __name__ == "__main__":
    # Test the connection
    test_connection()
