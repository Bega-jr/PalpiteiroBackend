from app.core.supabase import supabase
from typing import List, Optional
from uuid import UUID

def registrar_jogo(tipo: str, numeros: List[int], user_id: Optional[UUID] = None, **kwargs):
    """
    Salva um jogo no histórico do cliente no Supabase, vinculando ao próximo concurso.
    """
    # Importação local para evitar importação circular
    from app.services.estatisticas_service import obter_proximo_concurso
    
    # Define o concurso alvo: usa o enviado ou descobre o próximo pelo CSV
    concurso_alvo = kwargs.get("concurso_alvo") or obter_proximo_concurso()

    dados = {
        "tipo": tipo,
        "numeros": numeros,
        "user_id": str(user_id) if user_id else None,
        "concurso_alvo": concurso_alvo,
        "valor_aposta": kwargs.get("valor_aposta", 3.0)
    }
    
    # Mapeia scores se existirem
    if "score_medio" in kwargs:
        dados["score"] = kwargs["score_medio"]
    elif "score" in kwargs:
        dados["score"] = kwargs["score"]

    return supabase.table("historico_jogos").insert(dados).execute()

def listar_historico(user_id: UUID):
    """
    Retorna apenas os jogos do cliente logado.
    """
    return (
        supabase
        .table("historico_jogos")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .execute()
        .data
    )

def _carregar_historico(user_id: Optional[UUID] = None):
    """
    Alias usado por outros serviços.
    """
    if not user_id:
        return []
    return listar_historico(user_id)

def resumo_financeiro(user_id: UUID):
    dados = listar_historico(user_id)
    total_apostado = sum(j.get("valor_aposta", 0) for j in dados)
    return {
        "total_jogos": len(dados),
        "total_apostado": total_apostado
    }

def salvar_jogo(*args, **kwargs):
    return registrar_jogo(*args, **kwargs)
