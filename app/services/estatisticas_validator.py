from app.services.estatisticas_service import calcular_metricas_jogo

NUMEROS_POR_JOGO = 15


def validar_estrutura(jogo):
    jogo_unico = set(jogo)

    return {
        "faltantes": max(0, NUMEROS_POR_JOGO - len(jogo_unico)),
        "repetidos": len(jogo) != len(jogo_unico),
        "total": len(jogo_unico)
    }


def calcular_penalidade_sequencia(maior_seq):
    if maior_seq <= 5:
        return 0.0
    if maior_seq <= 7:
        return 0.1
    return 0.2


def validar_jogo(jogo):
    metricas = calcular_metricas_jogo(jogo)

    penalidade_seq = calcular_penalidade_sequencia(metricas["maior_sequencia"])

    score_base = 0.5
    score_final = max(0, score_base - penalidade_seq)

    aprovado = (
        170 <= metricas["soma"] <= 210
        and 6 <= metricas["pares"] <= 9
        and score_final >= 0.3
    )

    return {
        "aprovado": aprovado,
        "metricas": metricas,
        "score_final": score_final,
        "penalidade_sequencia": penalidade_seq
    }
