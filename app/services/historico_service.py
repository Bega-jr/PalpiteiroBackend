import uuid
from datetime import datetime
from typing import List

from app.core.supabase import supabase
from app.models.historico_model import JogoHistorico


def salvar_jogo(
    tipo: str,
    numeros: list,
    score_medio=None,
    score_final=None,
    penalidade_sequencia=None,
    concurso_referente=None,
    acertos=None,
    valor_aposta=3.0,
    premio=0.0
):
    jogo = JogoHistorico(
        id=str(uuid.uuid4()),
        data=datetime.utcnow(),
        tipo=tipo,
        numeros=numeros,
        score_medio=score_medio,
        score_final=score_final,
        penalidade_sequencia=penalidade_sequencia,
        concurso_referente=concurso_referente,
        acertos=acertos,
        valor_aposta=valor_aposta,
        premio=premio
    )

    supabase.table("historico_jogos").insert({
        "id": jogo.id,
        "tipo": jogo.tipo,
        "numeros": jogo.numeros,
        "score_medio": jogo.score_medio,
        "score_final": jogo.score_final,
        "penalidade_sequencia": jogo.penalidade_sequencia,
        "concurso_referente": jogo.concurso_referente,
        "acertos": jogo.acertos,
        "valor_aposta": jogo.valor_aposta,
        "premio": jogo.premio,
    }).execute()

    return jogo


def listar_historico(limit=50):
    res = (
        supabase
        .table("historico_jogos")
        .select("*")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    return res.data
