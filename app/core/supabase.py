from supabase import create_client
import os
from fastapi import Header, HTTPException

# --- CONFIGURAÇÃO DO CLIENTE ---
url = os.getenv("SUPABASE_URL")
# Prioriza a ANON_KEY para operações de usuário e reserva a KEY para o que você definiu na Vercel
key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY")

if not url or not key:
    raise ValueError(f"Erro de configuração: URL ou KEY não encontradas. URL: {bool(url)}, KEY: {bool(key)}")

supabase = create_client(url, key)

# --- UTILITÁRIO DE AUTENTICAÇÃO ---

def obter_usuario_logado(authorization: str = Header(None)):
    """
    Dependência para rotas protegidas. 
    Lê o token JWT do cabeçalho 'Authorization' e valida no Supabase.
    """
    if not authorization:
        raise HTTPException(
            status_code=401, 
            detail="Acesso negado: Token de autorização ausente."
        )
    
    try:
        # O cabeçalho geralmente vem como "Bearer <TOKEN>"
        token = authorization.replace("Bearer ", "").strip()
        
        # Valida o token diretamente com o Supabase Auth
        resposta = supabase.auth.get_user(token)
        
        if not resposta.user:
            raise HTTPException(status_code=401, detail="Usuário não encontrado.")
            
        return resposta.user.id  # Retorna o UUID do usuário
        
    except Exception as e:
        raise HTTPException(
            status_code=401, 
            detail="Sessão inválida ou expirada. Faça login novamente."
        )
