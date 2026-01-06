import os
from supabase import create_client, Client

# Variável global para armazenar a instância do cliente (Singleton)
_supabase: Client | None = None

def get_supabase() -> Client:
    global _supabase

    if _supabase is None:
        # Busca as variáveis diretamente do ambiente (Vercel/Sistema)
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")

        # Validação para ajudar no debug caso as variáveis não estejam configuradas no painel da Vercel
        if not supabase_url or not supabase_key:
            raise ValueError(
                "Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_SERVICE_ROLE_KEY não definidas."
            )

        _supabase = create_client(
            supabase_url,
            supabase_key
        )

    return _supabase
