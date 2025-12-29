from app.core.supabase import supabase
from typing import List, Optional
from uuid import UUID

def registrar_jogo(tipo: str, numeros: List[int], user_id: Optional[UUID] = None, **kwargs):
    # Dados base
    dados = {
        "tipo": tipo,
        "numeros": numeros,
        "user_id": str(user_id) if user_id else None, # Aqui envia NULL real, não a string "None"
        "valor_aposta": kwargs.get("valor_aposta", 3.0)
    }
    
    if "score_medio" in kwargs:
        dados["score"] = kwargs["score_medio"]
    elif "score" in kwargs:
        dados["score"] = kwargs["score"]

    return supabase.table("historico_jogos").insert(dados).execute()

def _carregar_historico(user_id: Optional[UUID] = None):
    return listar_historico(user_id)

def listar_historico(user_id: Optional[UUID] = None):
    # Iniciamos a query
    query = supabase.table("historico_jogos").select("*")
    
    # IMPORTANTE: Só adiciona o filtro se user_id NÃO for None
    if user_id is not None:
        query = query.eq("user_id", str(user_id))
    
    result = query.order("created_at", desc=True).limit(100).execute()
    return result.data if result.data else []

def resumo_financeiro(user_id: UUID):
    # No resumo, o user_id geralmente é obrigatório
    dados = listar_historico(user_id)
    total_apostado = sum(j.get("valor_aposta", 0) for j in dados)

    return {
        "total_jogos": len(dados),
        "total_apostado": total_apostado
    }

def salvar_jogo(*args, **kwargs):
    return registrar_jogo(*args, **kwargs)
