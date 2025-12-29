from app.core.supabase import supabase
from typing import List, Optional
from uuid import UUID

def registrar_jogo(tipo: str, numeros: List[int], user_id: Optional[UUID] = None, **kwargs):
    """
    Função unificada para salvar jogos. 
    Aceita argumentos extras (**kwargs) vindos do palpites_service para evitar erros.
    """
    # Dados base obrigatórios no banco
    dados = {
        "tipo": tipo,
        "numeros": numeros,
        "user_id": str(user_id) if user_id else None,
        "valor_aposta": kwargs.get("valor_aposta", 3.0)
    }
    
    # Adiciona campos extras se eles existirem no banco (metadados)
    if "score_medio" in kwargs:
        dados["score"] = kwargs["score_medio"]
    elif "score" in kwargs:
        dados["score"] = kwargs["score"]

    return supabase.table("historico_jogos").insert(dados).execute()

# Alias para manter compatibilidade com estatisticas_service
def _carregar_historico(user_id: UUID):
    return listar_historico(user_id)

# Alias para se algum lugar ainda chamar salvar_jogo
def salvar_jogo(*args, **kwargs):
    return registrar_jogo(*args, **kwargs)

def listar_historico(user_id: UUID):
    return (
        supabase
        .table("historico_jogos")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
        .data
    )

def resumo_financeiro(user_id: UUID):
    dados = listar_historico(user_id)
    # Proteção para garantir que valor_aposta existe no dicionário
    total_apostado = sum(j.get("valor_aposta", 0) for j in dados)

    return {
        "total_jogos": len(dados),
        "total_apostado": total_apostado
    }

