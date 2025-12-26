import random
import datetime
from functools import lru_cache

from app.services.estatisticas_service import (
    obter_estatisticas_base,
    obter_estatisticas_com_score
)
from app.services.estatisticas_validator import (
    validar_jogo,
    validar_estrutura
)

# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15
QTD_FIXOS = 7
MODO_PADRAO = "free"  # free | vip


# =====================================================
# CLASSIFICAÇÃO ORIGINAL (BACKUP SEGURO)
# =====================================================

def classificar_numeros_basico():
    estatisticas = obter_estatisticas_base()

    return {
        "quentes": estatisticas.head(8)["numero"].tolist(),
        "equilibrados": estatisticas.iloc[8:16]["numero"].tolist(),
        "frios": estatisticas.iloc[16:22]["numero"].tolist()
    }


# =====================================================
# CLASSIFICAÇÃO COM SCORE (NOVA – SEGURA)
# =====================================================

def classificar_numeros():
    try:
        estatisticas = obter_estatisticas_com_score()

        return {
            "topo": estatisticas.head(10)["numero"].tolist(),
            "meio": estatisticas.iloc[10:18]["numero"].tolist(),
            "base": estatisticas.iloc[18:25]["numero"].tolist()
        }
    except Exception:
        # fallback absoluto (não quebra nada)
        return classificar_numeros_basico()


# =====================================================
# FIXOS (INTELIGENTES + TRAVADOS)
# =====================================================

def gerar_fixos(grupos):
    try:
        fixos = (
            random.sample(grupos["topo"], 3) +
            random.sample(grupos["meio"], 2) +
            random.sample(grupos["base"], 2)
        )
    except KeyError:
        # fallback antigo
        fixos = (
            random.sample(grupos["quentes"], 3) +
            random.sample(grupos["equilibrados"], 2) +
            random.sample(grupos["frios"], 2)
        )

    fixos = sorted(set(fixos))

    if len(fixos) != QTD_FIXOS:
        raise RuntimeError("Falha ao gerar fixos")

    return fixos


# =====================================================
# PALPITE FIXO DIÁRIO (CACHE)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()
    fixos = gerar_fixos(grupos)

    universo = list(
        set(range(1, 26)) - set(fixos)
    )

    complemento = random.sample(
        universo,
        NUMEROS_POR_JOGO - len(fixos)
    )

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

    tentativas = 0
    while len(palpites) < 7 and tentativas < 50:
        tentativas += 1

        fixos = gerar_fixos(grupos)

        universo = list(
            set(range(1, 26)) - set(fixos)
        )

        complemento = random.sample(
            universo,
            NUMEROS_POR_JOGO - len(fixos)
        )

        jogo = sorted(fixos + complemento)

        estrutura = validar_estrutura(jogo)
        estatistica = validar_jogo(jogo)

        if modo == "free":
            if not estatistica["aprovado"]:
                continue
            if estrutura["faltantes"] > 0 or estrutura["repetidos"]:
                continue

        palpites.append({
            "status": "ok",
            "numeros": jogo,
            "estatistica": estatistica
        })

    return palpites
