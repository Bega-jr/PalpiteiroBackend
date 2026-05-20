import itertools
import numpy as np


# =========================================================
# DISTÂNCIA ENTRE JOGOS
# =========================================================
def distancia_jaccard(a, b):

    sa = set(a)
    sb = set(b)

    inter = len(sa & sb)
    uniao = len(sa | sb)

    return 1 - (inter / uniao)


def distancia_hamming(a, b):

    return len(
        set(a) ^ set(b)
    )


def similaridade_pares(a, b):

    pa = set(
        itertools.combinations(
            sorted(a),
            2
        )
    )

    pb = set(
        itertools.combinations(
            sorted(b),
            2
        )
    )

    return len(pa & pb)


def similaridade_ternos(a, b):

    ta = set(
        itertools.combinations(
            sorted(a),
            3
        )
    )

    tb = set(
        itertools.combinations(
            sorted(b),
            3
        )
    )

    return len(ta & tb)


# =========================================================
# SCORE GLOBAL DE DIVERSIDADE
# =========================================================
def score_diversidade(jogo, jogos_existentes):

    if not jogos_existentes:
        return 1.0

    jaccards = []
    hammings = []
    pares = []
    ternos = []

    for j in jogos_existentes:

        nums = j["nums"]

        jaccards.append(
            distancia_jaccard(
                jogo,
                nums
            )
        )

        hammings.append(
            distancia_hamming(
                jogo,
                nums
            )
        )

        pares.append(
            similaridade_pares(
                jogo,
                nums
            )
        )

        ternos.append(
            similaridade_ternos(
                jogo,
                nums
            )
        )

    score = (

        np.mean(jaccards) * 0.35

        +

        (np.mean(hammings) / 15) * 0.35

        +

        (1 - (np.mean(pares) / 105)) * 0.15

        +

        (1 - (np.mean(ternos) / 455)) * 0.15
    )

    return round(float(score), 6)


# =========================================================
# FILTRO FINAL
# =========================================================
def diversidade_ok_v2(
    jogo,
    jogos,
    score_minimo=0.58
):

    score = score_diversidade(
        jogo,
        jogos
    )

    return score >= score_minimo
