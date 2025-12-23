from app.services.estatisticas_services import (
    obter_estatisticas_base,
    calcular_metricas_jogo
)

# =====================================================
# CONFIGURAÇÕES DE VALIDAÇÃO
# =====================================================

REGRAS_PADRAO = {
    "soma": (170, 210),
    "pares": (6, 9),
    "sequencia_max": 5
}


def validar_jogo(jogo, regras=REGRAS_PADRAO):
    """
    Valida um jogo com base em regras estatísticas fixas
    """

    metricas = calcular_metricas_jogo(jogo)

    validacoes = {
        "soma_ok": regras["soma"][0] <= metricas["soma"] <= regras["soma"][1],
        "pares_ok": regras["pares"][0] <= metricas["pares"] <= regras["pares"][1],
        "sequencia_ok": metricas["maior_sequencia"] <= regras["sequencia_max"]
    }

    aprovado = all(validacoes.values())

    return {
        "aprovado": aprovado,
        "metricas": metricas,
        "validacoes": validacoes
    }


def validar_jogo_com_estatisticas(jogo):
    """
    Valida um jogo e adiciona contexto estatístico real
    """

    estatisticas = obter_estatisticas_base()
    resultado = validar_jogo(jogo)

    mapa_freq = dict(zip(
        estatisticas["numero"],
        estatisticas["frequencia"]
    ))

    mapa_atraso = dict(zip(
        estatisticas["numero"],
        estatisticas["atraso"]
    ))

    resultado["contexto"] = {
        "frequencia_total": sum(mapa_freq[n] for n in jogo),
        "atraso_medio": round(
            sum(mapa_atraso[n] for n in jogo) / len(jogo), 2
        )
    }

    return resultado


def filtrar_jogos_validos(lista_jogos, minimo_validos=1):
    """
    Filtra jogos aprovados estatisticamente.
    Se não atingir o mínimo, lança erro (sem fallback falso).
    """

    validos = []

    for jogo in lista_jogos:
        r = validar_jogo(jogo)
        if r["aprovado"]:
            validos.append(jogo)

    if len(validos) < minimo_validos:
        raise RuntimeError("Nenhum jogo válido estatisticamente")

    return validos

