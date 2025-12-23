import random
import datetime
from functools import lru_cache

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


def _sortear(grupo, qtd):
    if not grupo:
        return []
    return random.sample(grupo, min(qtd, len(grupo)))


def classificar_numeros():
    """
    Classificação simples (fallback estável)
    """
    todos = list(range(1, TOTAL_NUMEROS + 1))

    random.shuffle(todos)

    return {
        "quentes": todos[:8],
        "equilibrados": todos[8:16],
        "frios": todos[16:22],
        "atrasados": todos[22:]
    }


# =====================================================
# PALPITE FIXO DIÁRIO (TRAVA OK)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()

    jogo = (
        _sortear(grupos["quentes"], 6) +
        _sortear(grupos["equilibrados"], 5) +
        _sortear(grupos["frios"], 4)
    )

    jogo = list(set(jogo))
    universo = list(range(1, TOTAL_NUMEROS + 1))

    while len(jogo) < NUMEROS_POR_JOGO:
        n = random.choice(universo)
        if n not in jogo:
            jogo.append(n)

    return sorted(jogo)


def gerar_palpite_fixo():
    """
    Palpite fixo público – 1 por dia
    """
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# 7 PALPITES SIMPLES
# =====================================================

def gerar_7_palpites():
    grupos = classificar_numeros()
    palpites = []

    configuracoes = [
        ("Palpite 1", 6, 5, 4),
        ("Palpite 2", 5, 6, 4),
        ("Palpite 3", 4, 7, 4),
        ("Palpite 4", 4, 6, 5),
        ("Palpite 5", 3, 5, 7),
        ("Palpite 6", 2, 5, 8),
    ]

    for nome, q, e, f in configuracoes:
        jogo = (
            _sortear(grupos["quentes"], q)
            + _sortear(grupos["equilibrados"], e)
            + _sortear(grupos["frios"], f)
        )

        jogo = list(set(jogo))
        universo = list(range(1, TOTAL_NUMEROS + 1))

        while len(jogo) < NUMEROS_POR_JOGO:
            n = random.choice(universo)
            if n not in jogo:
                jogo.append(n)

        palpites.append({
            "nome": nome,
            "numeros": sorted(jogo)
        })

    # Palpite 7 – totalmente aleatório
    palpites.append({
        "nome": "Palpite 7",
        "numeros": sorted(random.sample(range(1, 26), 15))
    })

    return palpites
