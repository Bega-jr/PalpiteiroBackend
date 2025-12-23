from app.services.estatisticas_services import (
    obter_estatisticas_base,
    calcular_metricas_jogo
)

# =====================================================
# REGRAS PADRÃO
# =====================================================

REGRAS_PADRAO = {
    "soma": (170, 210),
    "pares": (6, 9),
    "sequencia_max": 5
}


# =====================================================
# VALIDAÇÃO SIMPLES
# =====================================================

def validar_jogo(jogo, regras=REGRAS_PADRAO):
    metricas = calcular_metricas_jogo(jogo)

    validacoes = {
        "soma_ok": regras["soma"][0] <= metricas["soma"] <= regras["soma"][1],
        "pares_ok": regras["pares"][0] <= metricas["pares"] <= regras["pares"][1],
        "sequencia_ok": metricas["maior_sequencia"] <= regras["sequencia_max"]
    }

    return {
        "aprovado": all(validacoes.values()),
        "metricas": metricas,
        "validacoes": validacoes
    }


# =====================================================
# VALIDAÇÃO COM CONTEXTO REAL
# =====================================================

def validar_jogo_com_estatisticas(jogo):
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
            sum(mapa_atraso[n] for n in jogo if mapa_atraso[n] is not None) / len(jogo),
            2
        )
    }

    return resultado


# =====================================================
# FILTRO DE JOGOS (SEM FALLBACK)
# =====================================================

def filtrar_jogos_validos(lista_jogos):
    """
    Retorna SOMENTE jogos aprovados.
    Se nenhum passar, retorna lista vazia.
    """

    validos = []

    for jogo in lista_jogos:
        r = validar_jogo(jogo)
        if r["aprovado"]:
            validos.append(jogo)

    return validos

