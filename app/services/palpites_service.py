import random
import datetime
from functools import lru_cache

from app.services.estatisticas_services import obter_estatisticas_base
from app.services.estatisticas_validator import (
    validar_jogo,
    validar_estrutura
)

# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15
QTD_FIXOS = 7   # configurável
MODO_PADRAO = "free"  # free | vip


# =====================================================
# CLASSIFICAÇÃO DOS NÚMEROS (ESTATÍSTICA REAL)
# =====================================================

def classificar_numeros():
    estatisticas = obter_estatisticas_base()

    quentes = estatisticas.head(8)["numero"].tolist()
    equilibrados = estatisticas.iloc[8:16]["numero"].tolist()
    frios = estatisticas.iloc[16:22]["numero"].tolist()

    if not quentes or not equilibrados or not frios:
        raise RuntimeError("Estatísticas insuficientes para classificação")

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios
    }


# =====================================================
# FIXOS (TRAVADOS)
# =====================================================

def gerar_fixos(grupos):
    base = (
        random.sample(grupos["quentes"], 3) +
        random.sample(grupos["equilibrados"], 2) +
        random.sample(grupos["frios"], 2)
    )

    return sorted(set(base))


# =====================================================
# PALPITE FIXO DIÁRIO (CACHE)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()
    fixos = gerar_fixos(grupos)

    universo = list(
        set(grupos["quentes"] + grupos["equilibrados"] + grupos["frios"])
        - set(fixos)
    )

    complemento = random.sample(universo, NUMEROS_POR_JOGO - len(fixos))
    jogo = sorted(fixos + complemento)

    estrutura = validar_estrutura(jogo)
    if estrutura["faltantes"] > 0 or estrutura["repetidos"]:
        raise RuntimeError("Falha estrutural no palpite fixo")

    return jogo


def gerar_palpite_fixo():
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# PALPITES ESTATÍSTICOS (FREE / VIP)
# =====================================================

def gerar_7_palpites(modo=MODO_PADRAO):
    grupos = classificar_numeros()
    palpites = []

    for _ in range(7):
        fixos = gerar_fixos(grupos)

        universo = list(
            set(grupos["quentes"] + grupos["equilibrados"] + grupos["frios"])
            - set(fixos)
        )

        complemento = random.sample(
            universo,
            NUMEROS_POR_JOGO - len(fixos)
        )

        jogo = sorted(fixos + complemento)

        estrutura = validar_estrutura(jogo)
        estatistica = validar_jogo(jogo)

        # ===============================
        # FREE → BLOQUEIA
        # ===============================
        if modo == "free":
            if not estatistica["aprovado"]:
                continue
            if estrutura["faltantes"] > 0 or estrutura["repetidos"]:
                continue

        # ===============================
        # VIP → DEVOLVE PARA DECISÃO
        # ===============================
        else:
            if estrutura["faltantes"] > 0 or estrutura["repetidos"]:
                palpites.append({
                    "status": "intervencao_necessaria",
                    "jogo_parcial": jogo,
                    "estrutura": estrutura,
                    "estatistica": estatistica
                })
                continue

        palpites.append({
            "status": "ok",
            "numeros": jogo,
            "estatistica": estatistica
        })

    return palpites

