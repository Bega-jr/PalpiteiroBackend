import random
import numpy as np


# =========================================================
# CROSSOVER
# =========================================================
def crossover(pai, mae):

    filho = sorted(

        list(

            set(

                random.sample(
                    pai,
                    8
                )

                +

                random.sample(
                    mae,
                    7
                )
            )
        )
    )

    while len(filho) < 15:

        n = random.randint(1, 25)

        if n not in filho:
            filho.append(n)

    return sorted(filho[:15])


# =========================================================
# MUTAÇÃO
# =========================================================
def mutacao(
    jogo,
    taxa=0.10
):

    jogo = jogo.copy()

    if random.random() > taxa:
        return sorted(jogo)

    idx = random.randint(0, 14)

    disponiveis = [

        n for n in range(1, 26)
        if n not in jogo
    ]

    jogo[idx] = random.choice(
        disponiveis
    )

    return sorted(jogo)


# =========================================================
# EVOLUÇÃO
# =========================================================
def evoluir_populacao(
    populacao,
    elite_size=10
):

    if not populacao:
        return []

    populacao = sorted(

        populacao,

        key=lambda x: x["score"],

        reverse=True
    )

    elite = populacao[:elite_size]

    nova_populacao = elite.copy()

    while len(nova_populacao) < len(populacao):

        p1 = random.choice(elite)
        p2 = random.choice(elite)

        filho = crossover(
            p1["nums"],
            p2["nums"]
        )

        filho = mutacao(
            filho
        )

        score_filho = float(

            (
                p1["score"]
                +
                p2["score"]
            ) / 2
        )

        nova_populacao.append({

            "nums": filho,

            "score": score_filho,

            "origem": "genetico"
        })

    return nova_populacao


# =========================================================
# SCORE POPULAÇÃO
# =========================================================
def score_populacao(populacao):

    if not populacao:
        return 0.0

    scores = [

        p["score"]

        for p in populacao
    ]

    return {

        "media": round(
            float(np.mean(scores)),
            6
        ),

        "maximo": round(
            float(np.max(scores)),
            6
        ),

        "minimo": round(
            float(np.min(scores)),
            6
        ),

        "desvio": round(
            float(np.std(scores)),
            6
        )
    }


# =========================================================
# SELEÇÃO FINAL
# =========================================================
def selecionar_populacao_final(
    candidatos,
    qtd=7,
    diversidade_minima=8
):

    finais = []

    estruturas = set()

    for candidato in sorted(

        candidatos,

        key=lambda x: x["score"],

        reverse=True
    ):

        if len(finais) >= qtd:
            break

        nums = candidato["nums"]

        estrutura = tuple(

            candidato.get(
                "estrutura",
                {}
            ).get(
                "linhas",
                []
            )
        )

        # =====================================
        # EVITA ESTRUTURAS IGUAIS
        # =====================================
        if estrutura in estruturas:
            continue

        # =====================================
        # DIVERSIDADE
        # =====================================
        valido = True

        for existente in finais:

            diferenca = len(

                set(nums)
                ^
                set(existente["nums"])
            )

            if diferenca < diversidade_minima:

                valido = False
                break

        if not valido:
            continue

        estruturas.add(
            estrutura
        )

        finais.append(candidato)

    return finais
