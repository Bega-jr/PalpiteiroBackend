import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não definidos")

_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase

    if _supabase is None:
        _supabase = create_client(
            SUPABASE_URL,
            SUPABASE_SERVICE_KEY
        )

    return _supabase
