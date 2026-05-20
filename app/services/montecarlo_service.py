import random
import numpy as np


# =========================================================
# SIMULAÇÃO
# =========================================================
def simular_concurso():

    return set(

        random.sample(
            range(1, 26),
            15
        )
    )


def avaliar_jogo(
    jogo,
    simulacoes=5000
):

    resultados = []

    jogo = set(jogo)

    for _ in range(simulacoes):

        concurso = simular_concurso()

        acertos = len(
            jogo & concurso
        )

        resultados.append(acertos)

    return {

        "media": round(
            float(np.mean(resultados)),
            6
        ),

        "desvio": round(
            float(np.std(resultados)),
            6
        ),

        "max": max(resultados),

        "min": min(resultados)
    }


# =========================================================
# SCORE MONTE CARLO
# =========================================================
def score_montecarlo(jogo):

    stats = avaliar_jogo(jogo)

    score = (

        stats["media"] * 0.60

        +

        stats["max"] * 0.25

        -

        stats["desvio"] * 0.15
    )

    return round(float(score), 6)
