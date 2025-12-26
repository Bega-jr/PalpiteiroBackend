from app.services.estatisticas_service import calcular_metricas_jogo

NUMEROS_POR_JOGO = 15

def validar_estrutura(jogo):
    jogo_unico = set(jogo)

    return {
        "faltantes": max(0, NUMEROS_POR_JOGO - len(jogo_unico)),
        "repetidos": len(jogo) != len(jogo_unico),
        "total": len(jogo_unico)
    }


def validar_jogo(jogo):
    metricas = calcular_metricas_jogo(jogo)

    aprovado = (
        170 <= metricas["soma"] <= 210
        and 6 <= metricas["pares"] <= 9
        and metricas["maior_sequencia"] <= 5
    )

    return {
        "aprovado": aprovado,
        "metricas": metricas
    }
