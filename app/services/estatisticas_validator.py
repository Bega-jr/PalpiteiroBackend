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


# =====================================================
# VALIDAÇÃO PRINCIPAL
# =====================================================

def validar_jogo(jogo, regras=REGRAS_PADRAO):
    """
    Valida um jogo estatisticamente com base em regras configuráveis
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


# =====================================================
# VALIDAÇÃO COM CONTEXTO ESTATÍSTICO
# =====================================================

def validar_jogo_com_estatisticas(jogo):
    """
    Valida o jogo e adiciona contexto estatístico (frequência e atraso)
    """

    estatisticas = obter_estatisticas_base()
    resultado = validar_jogo(jogo)

    if estatisticas is None or estatisticas.empty:
        return resultado

    mapa_freq = dict(zip(
        estatisticas["numero"],
        estatisticas["frequencia"]
    ))

    mapa_atraso = dict(zip(
        estatisticas["numero"],
        estatisticas["atraso"]
    ))

    freq_total = sum(mapa_freq.get(n, 0) for n in jogo)
    atraso_medio = round(
        sum(mapa_atraso.get(n, 0) for n in jogo) / len(jogo), 2
    )

    resultado["contexto"] = {
        "frequencia_total": freq_total,
        "atraso_medio": atraso_medio
    }

    return resultado


# =====================================================
# VALIDAÇÃO EM LOTE
# =====================================================

def filtrar_jogos_validos(lista_jogos, minimo_validos=1):
    """
    Filtra jogos válidos a partir de uma lista
    """

    validos = []
    rejeitados = []

    for jogo in lista_jogos:
        r = validar_jogo(jogo)
        if r["aprovado"]:
            validos.append(jogo)
        else:
            rejeitados.append({
                "jogo": jogo,
                "motivo": r["validacoes"]
            })

    # fallback de segurança
    if len(validos) < minimo_validos:
        return lista_jogos[:minimo_validos]

    return validos
