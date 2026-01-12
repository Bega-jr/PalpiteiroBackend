from app.services.supabase_service import get_supabase
from app.services.palpites_service import gerar_palpites_validos
from datetime import date
import json


# ==========================
# UTILIDADES
# ==========================

def _comparar(palpite, resultado):
    return len(set(palpite) & set(resultado))


# ==========================
# BACKTEST PRINCIPAL
# ==========================

def executar_backtest(
    concurso_inicio: int,
    concurso_fim: int,
    qtd_palpites: int = 7
):
    supabase = get_supabase()

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso, numeros")
        .gte("concurso", concurso_inicio)
        .lte("concurso", concurso_fim)
        .order("concurso")
        .execute()
        .data
    )

    if not concursos:
        raise Exception("Concursos não encontrados")

    resumo = {
        "total_concursos": len(concursos),
        "melhor_acerto": 0,
        "media_acertos": 0,
        "acertos_11+": 0,
        "acertos_12+": 0,
        "acertos_13+": 0
    }

    total_acertos = 0

    for conc in concursos:
        resultado = conc["numeros"]
        melhor_do_concurso = 0

        # gera palpites simulados (não salva)
        simulacao = gerar_palpites_simulados(qtd_palpites)

        for palpite in simulacao:
            acertos = _comparar(palpite, resultado)
            melhor_do_concurso = max(melhor_do_concurso, acertos)

        total_acertos += melhor_do_concurso
        resumo["melhor_acerto"] = max(resumo["melhor_acerto"], melhor_do_concurso)

        if melhor_do_concurso >= 11:
            resumo["acertos_11+"] += 1
        if melhor_do_concurso >= 12:
            resumo["acertos_12+"] += 1
        if melhor_do_concurso >= 13:
            resumo["acertos_13+"] += 1

    resumo["media_acertos"] = round(
        total_acertos / resumo["total_concursos"], 2
    )

    return resumo


# ==========================
# GERADOR SEM PERSISTÊNCIA
# ==========================

def gerar_palpites_simulados(qtd_palpites=7):
    """
    Replica a lógica do gerar_palpites_validos
    SEM gravar no banco
    """
    from app.services.palpites_service import _buscar_estatisticas
    import random

    estatisticas = _buscar_estatisticas()

    pool = []
    for e in estatisticas:
        score = float(e.get("score") or 0)
        atraso = float(e.get("atraso") or 0)
        tendencia = float(e.get("tendencia") or 0)

        peso = (
            score * 0.5 +
            (1 / (atraso + 1)) * 0.3 +
            tendencia * 0.2
        )
        pool.append((e["numero"], max(peso, 0.01)))

    palpites = []

    for _ in range(qtd_palpites):
        while True:
            numeros = sorted(
                set(
                    random.choices(
                        [n for n, _ in pool],
                        weights=[p for _, p in pool],
                        k=15
                    )
                )
            )
            if len(numeros) == 15:
                palpites.append(numeros)
                break

    return palpites
