import math
import numpy as np

from collections import Counter


# =========================================================
# HELPERS
# =========================================================
def distancia_jaccard(a, b):

    a = set(a)
    b = set(b)

    inter = len(a & b)
    uniao = len(a | b)

    if uniao == 0:
        return 0.0

    return 1 - (inter / uniao)


def calcular_centroide(jogos):

    if not jogos:
        return []

    freq = Counter()

    for jogo in jogos:
        freq.update(jogo)

    mais_comuns = [

        n

        for n, _ in freq.most_common(15)
    ]

    return sorted(mais_comuns)


def calcular_similaridade_estrutura(j1, j2):

    linhas1 = calcular_linhas(j1)
    linhas2 = calcular_linhas(j2)

    diferenca = sum(

        abs(a - b)

        for a, b in zip(linhas1, linhas2)
    )

    return max(
        0.0,
        1 - (diferenca / 15)
    )


def calcular_linhas(nums):

    return [

        sum(1 for n in nums if 1 <= n <= 5),

        sum(1 for n in nums if 6 <= n <= 10),

        sum(1 for n in nums if 11 <= n <= 15),

        sum(1 for n in nums if 16 <= n <= 20),

        sum(1 for n in nums if 21 <= n <= 25)
    ]


# =========================================================
# CLUSTER
# =========================================================
def identificar_cluster_jogo(
    jogo,
    clusters_existentes=None
):

    nums = sorted(jogo)

    linhas = calcular_linhas(nums)

    pares = sum(
        1 for n in nums
        if n % 2 == 0
    )

    soma = sum(nums)

    assinatura = (

        f"L{'-'.join(map(str, linhas))}"
        f"_P{pares}"
        f"_S{int(round(soma / 10) * 10)}"
    )

    if not clusters_existentes:

        return {

            "cluster_id": assinatura,

            "similaridade_media": 0.0,

            "densidade_cluster": 0.0,

            "centroide": nums
        }


    similares = []

    for cluster in clusters_existentes:

        jogo_ref = cluster.get(
            "centroide",
            []
        )

        if not jogo_ref:
            continue

        dist = distancia_jaccard(
            nums,
            jogo_ref
        )

        similaridade = 1 - dist

        similares.append(
            similaridade
        )


    similaridade_media = (

        float(np.mean(similares))
        if similares
        else 0.0
    )

    densidade = min(
        1.0,
        similaridade_media * 1.25
    )

    return {

        "cluster_id": assinatura,

        "similaridade_media": round(
            similaridade_media,
            6
        ),

        "densidade_cluster": round(
            densidade,
            6
        ),

        "centroide": nums
    }


# =========================================================
# AGRUPAMENTO
# =========================================================
def gerar_clusters(jogos):

    clusters = {}

    for jogo in jogos:

        cluster = identificar_cluster_jogo(
            jogo
        )

        cid = cluster["cluster_id"]

        if cid not in clusters:

            clusters[cid] = []

        clusters[cid].append(jogo)


    resultado = []

    for cid, jogos_cluster in clusters.items():

        centroide = calcular_centroide(
            jogos_cluster
        )

        resultado.append({

            "cluster_id": cid,

            "qtd_jogos": len(jogos_cluster),

            "centroide": centroide,

            "densidade": round(

                min(
                    1.0,
                    len(jogos_cluster) / 50
                ),

                6
            )
        })

    return resultado


# =========================================================
# SCORE CLUSTER
# =========================================================
def score_clusterizacao(cluster_info):

    if not cluster_info:
        return 1.0

    similaridade = float(
        cluster_info.get(
            "similaridade_media",
            0
        )
    )

    densidade = float(
        cluster_info.get(
            "densidade_cluster",
            0
        )
    )

    score = (

        1.0

        +

        (similaridade * 0.08)

        -

        (densidade * 0.05)
    )

    return round(
        max(0.85, min(1.15, score)),
        6
    )
