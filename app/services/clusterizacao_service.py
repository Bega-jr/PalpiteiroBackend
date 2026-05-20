import random
import numpy as np

from collections import defaultdict


# =========================================================
# KMEANS SIMPLES
# =========================================================
def distancia(a, b):

    return np.linalg.norm(
        np.array(a) - np.array(b)
    )


def clusterizar(candidatos, k=4):

    if len(candidatos) < k:
        return [candidatos]

    centroides = random.sample(
        [
            c["vetor"]
            for c in candidatos
        ],
        k
    )

    for _ in range(15):

        grupos = defaultdict(list)

        for c in candidatos:

            dists = [

                distancia(
                    c["vetor"],
                    centro
                )

                for centro in centroides
            ]

            idx = int(np.argmin(dists))

            grupos[idx].append(c)

        novos_centros = []

        for i in range(k):

            grupo = grupos[i]

            if not grupo:

                novos_centros.append(
                    random.choice(
                        candidatos
                    )["vetor"]
                )

                continue

            media = np.mean(

                [
                    g["vetor"]
                    for g in grupo
                ],

                axis=0
            )

            novos_centros.append(media)

        centroides = novos_centros

    return list(grupos.values())
