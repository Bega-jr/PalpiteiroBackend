import random
import datetime
from functools import lru_cache

from app.services.estatisticas_services import obter_estatisticas_base

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


def classificar_numeros():
    estatisticas = obter_estatisticas_base()

    quentes = estatisticas.head(8)["numero"].tolist()
    equilibrados = estatisticas.iloc[8:16]["numero"].tolist()
    frios = estatisticas.iloc[16:22]["numero"].tolist()
    atrasados = (
        estatisticas
        .sort_values("atraso", ascending=False)
        .head(8)["numero"]
        .tolist()
    )

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }


# =====================================================
# PALPITE FIXO (1 POR DIA — SEGURO)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()

    jogo = (
        random.sample(grupos["quentes"], 6) +
        random.sample(grupos["equilibrados"], 5) +
        random.sample(grupos["frios"], 4)
    )

    if len(set(jogo)) != NUMEROS_POR_JOGO:
        raise RuntimeError("Erro ao gerar palpite fixo")

    return sorted(jogo)


def gerar_palpite_fixo():
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# 7 PALPITES ESTATÍSTICOS
# =====================================================

def gerar_7_palpites():
    grupos = classificar_numeros()

    configuracoes = [
        ("Palpite 1", 8, 5, 2),
        ("Palpite 2", 7, 6, 2),
        ("Palpite 3", 5, 7, 3),
        ("Palpite 4", 4, 6, 5),
        ("Palpite 5", 3, 4, 8),
        ("Palpite 6", 2, 3, 10),
    ]

    palpites = []

    for nome, q, e, f in configuracoes:
        jogo = (
            random.sample(grupos["quentes"], q) +
            random.sample(grupos["equilibrados"], e) +
            random.sample(grupos["frios"], f)
        )

        if len(set(jogo)) != NUMEROS_POR_JOGO:
            raise RuntimeError(f"Erro ao montar {nome}")

        palpites.append({
            "nome": nome,
            "numeros": sorted(jogo)
        })

    # Palpite 7 — atrasados
    jogo7 = (
        grupos["atrasados"] +
        grupos["equilibrados"]
    )[:NUMEROS_POR_JOGO]

    if len(jogo7) != NUMEROS_POR_JOGO:
        raise RuntimeError("Erro no palpite atrasado")

    palpites.append({
        "nome": "Palpite 7",
        "numeros": sorted(jogo7)
    })

    return palpites

