import random
import datetime
from functools import lru_cache

from app.services.estatisticas_services import obter_estatisticas_base
from app.services.estatisticas_validator import filtrar_jogos_validos

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


def classificar_numeros():
    """
    Classifica números usando estatísticas reais
    """

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

    if not all([quentes, equilibrados, frios, atrasados]):
        raise RuntimeError("Classificação estatística incompleta")

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }


# =====================================================
# PALPITE FIXO (CACHE DIÁRIO)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()

    jogo = (
        random.sample(grupos["quentes"], 6) +
        random.sample(grupos["equilibrados"], 5) +
        random.sample(grupos["frios"], 4)
    )

    if len(set(jogo)) != 15:
        raise RuntimeError("Falha ao gerar palpite fixo consistente")

    return sorted(jogo)


def gerar_palpite_fixo():
    """
    Palpite fixo público – 1 por dia
    """
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# 7 PALPITES ESTATÍSTICOS
# =====================================================

def gerar_7_palpites():
    grupos = classificar_numeros()

    configuracoes = [
        ("Palpite 1 - Muito Quente", 8, 5, 2),
        ("Palpite 2 - Quente", 7, 6, 2),
        ("Palpite 3 - Equilibrado Quente", 5, 7, 3),
        ("Palpite 4 - Equilibrado Frio", 4, 6, 5),
        ("Palpite 5 - Frio", 3, 4, 8),
        ("Palpite 6 - Muito Frio", 2, 3, 10),
    ]

    palpites = []

    for nome, q, e, f in configuracoes:
        jogo = (
            random.sample(grupos["quentes"], q) +
            random.sample(grupos["equilibrados"], e) +
            random.sample(grupos["frios"], f)
        )

        jogo = sorted(set(jogo))

        if len(jogo) != 15:
            raise RuntimeError(f"Falha ao montar {nome}")

        palpites.append({
            "nome": nome,
            "numeros": jogo
        })

    # Palpite 7 – atrasados com fechamento
    jogo7 = (
        grupos["atrasados"] +
        grupos["equilibrados"]
    )[:15]

    if len(jogo7) != 15:
        raise RuntimeError("Falha ao gerar palpite atrasado")

    palpites.append({
        "nome": "Palpite 7 - Atrasados",
        "numeros": sorted(jogo7)
    })

    # Validação final obrigatória
    jogos_validos = filtrar_jogos_validos(
        [p["numeros"] for p in palpites],
        minimo_validos=1
    )

    return palpites

