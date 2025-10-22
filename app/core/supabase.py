from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()

# Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

# Client instance
supabase_client: Client = None

def get_supabase_client() -> Client:
    """
    Supabase client instance döndür
    """
    global supabase_client
    
    if supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase credentials bulunamadı!")
        
        supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase client oluşturuldu")
    
    return supabase_client

def get_supabase_admin_client() -> Client:
    """
    Supabase admin client (service role key ile)
    RLS politikalarını bypass eder
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Supabase service key bulunamadı!")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)