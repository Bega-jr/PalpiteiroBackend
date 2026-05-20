import random
import numpy as np


# =========================================================
# HELPERS
# =========================================================
def similaridade(a, b):

    return len(
        set(a) & set(b)
    )


def distancia_media(
    jogo,
    selecionados
):

    if not selecionados:
        return 15.0

    distancias = []

    for s in selecionados:

        overlap = similaridade(
            jogo,
            s["nums"]
        )

        distancias.append(
            15 - overlap
        )

    return float(
        np.mean(distancias)
    )


# =========================================================
# SELEÇÃO GENÉTICA
# =========================================================
def selecionar_populacao_final(

    candidatos,

    qtd_final=7,

    diversidade_minima=4,

    elite_inicial=80,

    **kwargs
):

    if not candidatos:
        return []

    # =====================================================
    # ELITE
    # =====================================================
    elite = candidatos[:elite_inicial]

    finais = []

    clusters_usados = set()

    # =====================================================
    # PRIMEIRA PASSAGEM
    # =====================================================
    for c in elite:

        if len(finais) >= qtd_final:
            break

        cluster = c.get(
            "cluster_id",
            -1
        )

        jogo = c["nums"]

        # =================================================
        # DIVERSIDADE
        # =================================================
        dist = distancia_media(
            jogo,
            finais
        )

        if dist < diversidade_minima:
            continue

        # =================================================
        # SATURAÇÃO DE CLUSTER
        # =================================================
        if cluster in clusters_usados:

            if random.random() < 0.65:
                continue

        finais.append(c)

        clusters_usados.add(cluster)

    # =====================================================
    # FALLBACK
    # =====================================================
    if len(finais) < qtd_final:

        restantes = [

            c for c in elite
            if c not in finais
        ]

        random.shuffle(restantes)

        for c in restantes:

            if len(finais) >= qtd_final:
                break

            finais.append(c)

    # =====================================================
    # ORDENA FINAL
    # =====================================================
    finais.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    return finais[:qtd_final]
