import random
import numpy as np


# =========================================================
# HELPERS
# =========================================================
def calcular_acertos(
    jogo,
    sorteio
):

    return len(
        set(jogo) & set(sorteio)
    )


# =========================================================
# MONTE CARLO
# =========================================================
def simular_probabilidade_jogo(
    jogo,
    historico=None,
    simulacoes=300,
    **kwargs
):

    # =====================================================
    # FALLBACK
    # =====================================================
    if not historico:

        historico = []

        for _ in range(simulacoes):

            historico.append({

                "numeros": sorted(
                    random.sample(
                        range(1, 26),
                        15
                    )
                )
            })

    resultados = []

    # =====================================================
    # SIMULAÇÃO HISTÓRICA
    # =====================================================
    for concurso in historico[-simulacoes:]:

        dezenas = concurso.get(
            "numeros",
            []
        )

        acertos = calcular_acertos(
            jogo,
            dezenas
        )

        resultados.append(acertos)

    if not resultados:
        return 0.0

    media = float(
        np.mean(resultados)
    )

    estabilidade = 1 - min(
        np.std(resultados) / 5,
        1
    )

    score = (

        (media / 15) * 0.75

        +

        (estabilidade * 0.25)
    )

    return round(
        float(score),
        6
    )
