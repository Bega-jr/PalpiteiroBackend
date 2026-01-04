import os

SUPABASE_URL = os.getenv("SUPABASE_URL")

SUPABASE_SERVICE_KEY = (
    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    or os.getenv("SUPABASE_SERVICE_KEY")
    or os.getenv("SUPABASE_KEY")
)

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Variáveis SUPABASE não configuradas corretamente")
