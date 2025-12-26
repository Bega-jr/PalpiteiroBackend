from app.services.estatisticas_service import calcular_metricas_jogo

NUMEROS_POR_JOGO = 15
SCORE_MINIMO = 0.30  # ajuste fino depois se quiser


def validar_estrutura(jogo):
    jogo_unico = set(jogo)

    return {
        "faltantes": max(0, NUMEROS_POR_JOGO - len(jogo_unico)),
        "repetidos": len(jogo) != len(jogo_unico),
        "total": len(jogo_unico)
    }


def penalidade_sequencia(maior_sequencia):
    """
    Penalização progressiva por sequências longas
    """
    if maior_sequencia <= 4:
        return 0.0
    elif maior_sequencia == 5:
        return 0.05
    elif maior_sequencia == 6:
        return 0.10
    else:  # 7 ou mais
        return 0.20


def validar_jogo(jogo, score_base=0.5):
    metricas = calcular_metricas_jogo(jogo)

    # Penalidade por sequência
    penalidade = penalidade_sequencia(metricas["maior_sequencia"])
    score_final = max(0, score_base - penalidade)

    aprovado = (
        170 <= metricas["soma"] <= 210
        and 6 <= metricas["pares"] <= 9
        and score_final >= SCORE_MINIMO
    )

    return {
        "aprovado": aprovado,
        "metricas": metricas,
        "score_final": round(score_final, 3),
        "penalidade_sequencia": penalidade
    }
