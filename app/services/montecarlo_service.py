import random
import numpy as np


# =========================================================
# SIMULAÇÃO
# =========================================================
def gerar_sorteio():

    return sorted(

        random.sample(
            range(1, 26),
            15
        )
    )


def calcular_acertos(
    jogo,
    sorteio
):

    return len(
        set(jogo)
        &
        set(sorteio)
    )


# =========================================================
# MONTE CARLO
# =========================================================
def simular_probabilidade_jogo(
    jogo,
    simulacoes=5000
):

    resultados = {

        11: 0,
        12: 0,
        13: 0,
        14: 0,
        15: 0
    }

    acertos_lista = []


    for _ in range(simulacoes):

        sorteio = gerar_sorteio()

        acertos = calcular_acertos(
            jogo,
            sorteio
        )

        acertos_lista.append(
            acertos
        )

        if acertos >= 11:

            resultados[acertos] += 1


    probs = {

        f"prob_{k}": round(
            v / simulacoes,
            8
        )

        for k, v in resultados.items()
    }


    media = float(
        np.mean(acertos_lista)
    )

    dp = float(
        np.std(acertos_lista)
    )


    score_probabilistico = (

        (probs["prob_11"] * 0.35)

        +

        (probs["prob_12"] * 0.30)

        +

        (probs["prob_13"] * 0.20)

        +

        (probs["prob_14"] * 0.10)

        +

        (probs["prob_15"] * 0.05)
    )


    return {

        **probs,

        "media_acertos": round(
            media,
            6
        ),

        "desvio_padrao": round(
            dp,
            6
        ),

        "score_probabilistico": round(
            score_probabilistico,
            10
        )
    }


# =========================================================
# SCORE FINAL
# =========================================================
def bonus_montecarlo(resultado):

    score = float(
        resultado.get(
            "score_probabilistico",
            0
        )
    )

    media = float(
        resultado.get(
            "media_acertos",
            0
        )
    )

    bonus = 1.0

    if media >= 9:
        bonus += 0.04

    elif media >= 8:
        bonus += 0.02

    bonus += min(
        score * 100,
        0.08
    )

    return round(
        bonus,
        6
    )
