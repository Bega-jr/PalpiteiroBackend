from app.services.estatisticas_services import calcular_metricas_jogo


# =====================================================
# REGRAS PADRÃO (CONFIGURÁVEL)
# =====================================================

REGRAS_PADRAO = {
    "soma": (170, 210),
    "pares": (6, 9),
    "sequencia_max": 5
}


# =====================================================
# VALIDAÇÃO ESTATÍSTICA
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
# VALIDAÇÃO ESTRUTURAL (SEM CORREÇÃO AUTOMÁTICA)
# =====================================================

def validar_estrutura(jogo):
    return {
        "quantidade": len(jogo),
        "repetidos": len(jogo) != len(set(jogo)),
        "faltantes": max(0, 15 - len(jogo))
    }
