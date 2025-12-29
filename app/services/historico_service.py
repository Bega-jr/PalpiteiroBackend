from app.core.supabase import supabase
from typing import List
from uuid import UUID


def salvar_jogo(
    user_id: UUID,
    tipo: str,
    numeros: List[int],
    score: float | None = None,
    valor_aposta: float = 3.0
):
    return supabase.table("historico_jogos").insert({
        "user_id": str(user_id),
        "tipo": tipo,
        "numeros": numeros,
        "score": score,
        "valor_aposta": valor_aposta
    }).execute()


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

    total_apostado = sum(j["valor_aposta"] for j in dados)

    return {
        "total_jogos": len(dados),
        "total_apostado": total_apostado
    }

