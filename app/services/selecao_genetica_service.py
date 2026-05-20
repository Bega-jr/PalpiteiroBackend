import random


# =========================================================
# CROSSOVER
# =========================================================
def crossover(a, b):

    pai = set(a)
    mae = set(b)

    filho = list(

        set(
            random.sample(
                list(pai),
                8
            )

            +

            random.sample(
                list(mae),
                7
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
def mutacao(jogo, taxa=0.10):

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
def evoluir(populacao):

    nova = []

    elite = populacao[:10]

    nova.extend(elite)

    while len(nova) < len(populacao):

        p1 = random.choice(elite)
        p2 = random.choice(elite)

        filho = crossover(
            p1["nums"],
            p2["nums"]
        )

        filho = mutacao(filho)

        nova.append({

            "nums": filho,
            "score": (
                p1["score"]
                +
                p2["score"]
            ) / 2
        })

    return nova
