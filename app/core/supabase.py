from supabase import create_client
import os

# --- CONFIGURAÇÃO DO CLIENTE ---
# Usamos os.environ.get para garantir compatibilidade com o GitHub Actions
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

# Só validamos se não estivermos em um ambiente de build ou se for execução real
if not url or not key:
    # Se estiver rodando no GitHub, isso vai ajudar a identificar qual falta
    print(f"Debug Environment: URL existe: {bool(url)}, KEY existe: {bool(key)}")
    raise ValueError("Erro: Variáveis de ambiente SUPABASE_URL ou SUPABASE_KEY não configuradas.")

supabase = create_client(url, key)

# --- UTILITÁRIO DE AUTENTICAÇÃO ---
# Importamos o FastAPI apenas dentro da função para evitar que o GitHub Action
# dê erro se a lib não estiver totalmente carregada ou necessária
def obter_usuario_logado(authorization: str = None):
    from fastapi import Header, HTTPException
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
