import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega o .env explicitamente (Python 3.12 safe)
load_dotenv(dotenv_path=".env")

# Singleton do cliente Supabase
_supabase: Client | None = None


def get_supabase() -> Client:
    global _supabase

    if _supabase is None:
        supabase_url = os.getenv("SUPABASE_URL")

        # aceita múltiplos nomes de chave (compatível com seu .env atual)
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

        _supabase = create_client(
            supabase_url,
            supabase_key
        )

    return _supabase
