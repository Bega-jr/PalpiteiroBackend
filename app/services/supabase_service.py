import os
from pathlib import Path
from threading import Lock
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

# Singleton do cliente Supabase
_supabase: Client | None = None
_supabase_lock = Lock()


def get_supabase() -> Client:
    global _supabase

    if _supabase is None:
        with _supabase_lock:
            if _supabase is None:
                supabase_url = os.getenv("SUPABASE_URL")
                supabase_key = (
                    os.getenv("SUPABASE_SERVICE_ROLE_KEY")
                    or os.getenv("SUPABASE_ANON_KEY")
                    or os.getenv("SUPABASE_KEY")
                )

                if not supabase_url or not supabase_key:
                    raise ValueError(
                        "Erro: SUPABASE_URL ou chave do Supabase não definida "
                        "(SERVICE_ROLE, ANON ou SUPABASE_KEY)."
                    )

                _supabase = create_client(supabase_url, supabase_key)

    assert _supabase is not None
    return _supabase
