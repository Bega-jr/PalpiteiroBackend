from supabase import create_client
import os
from dotenv import load_dotenv

# 🔹 GARANTE carregamento do .env em scripts, cron, codespace e local
load_dotenv()

# --- CONFIGURAÇÃO DO CLIENTE ---
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

# Debug explícito (ajuda muito em scripts)
print(f"Debug Environment: URL existe: {bool(url)}, KEY existe: {bool(key)}")

if not url or not key:
    raise ValueError(
        "Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas."
    )

supabase = create_client(url, key)


def get_supabase():
    """Retorna o client Supabase (padrão para scripts)"""
    return supabase


# --- UTILITÁRIO DE AUTENTICAÇÃO (API) ---
def obter_usuario_logado(authorization: str = None):
    from fastapi import HTTPException

    if not authorization:
        raise HTTPException(status_code=401, detail="Token ausente")

    try:
        token = authorization.replace("Bearer ", "").strip()
        resposta = supabase.auth.get_user(token)

        if not resposta.user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado")

        return resposta.user.id

    except Exception:
        raise HTTPException(status_code=401, detail="Sessão inválida")
