import math
import numpy as np

from collections import Counter


PRIMOS = {
    2, 3, 5, 7, 11,
    13, 17, 19, 23
}


MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15,
    16, 20, 21, 22,
    23, 24, 25
}


# =========================================================
# HELPERS
# =========================================================
def calcular_entropia(nums):

    freq = Counter(nums)

    probs = [

        v / len(nums)

        for v in freq.values()
    ]

    return float(

        -sum(

            p * math.log2(p)

            for p in probs
        )
    )


def calcular_sequencias(nums):

    nums = sorted(nums)

    seq = 1
    atual = 1

    for i in range(len(nums) - 1):

        if nums[i + 1] == nums[i] + 1:

            atual += 1

            seq = max(seq, atual)

        else:

            atual = 1

    return seq


def calcular_linhas(nums):

    return [

        sum(1 for n in nums if 1 <= n <= 5),

        sum(1 for n in nums if 6 <= n <= 10),

        sum(1 for n in nums if 11 <= n <= 15),

        sum(1 for n in nums if 16 <= n <= 20),

        sum(1 for n in nums if 21 <= n <= 25)
    ]


def calcular_colunas(nums):

    colunas = []

    for c in range(1, 6):

        colunas.append(

            sum(

                1 for n in nums

                if (n - c) % 5 == 0
            )
        )

    return colunas


# =========================================================
# FEATURE ENGINE
# =========================================================
def gerar_features_jogo(
    jogo,
    filtros=None,
    estrutura=None,
    cluster=None,
    montecarlo=None,
    ultimo=None
):

    nums = sorted(jogo)

    # =====================================================
    # FILTROS BASE
    # =====================================================
    pares = sum(

        1 for n in nums

        if n % 2 == 0
    )

    impares = 15 - pares

    primos = sum(

        1 for n in nums

        if n in PRIMOS
    )

    moldura = sum(

        1 for n in nums

        if n in MOLDURA
    )

    soma = sum(nums)

    repetidos = 0

    if ultimo:

        repetidos = len(
            set(nums) & set(ultimo)
        )


    # =====================================================
    # ESTRUTURA
    # =====================================================
    linhas = (

        estrutura["linhas"]

        if estrutura and "linhas" in estrutura

        else calcular_linhas(nums)
    )

    colunas = calcular_colunas(nums)

    quadrantes = [

        sum(1 for n in nums if n <= 7),

        sum(1 for n in nums if 8 <= n <= 13),

        sum(1 for n in nums if 14 <= n <= 19),

        sum(1 for n in nums if n >= 20)
    ]


    # =====================================================
    # FEATURES AVANÇADAS
    # =====================================================
    seq_max = calcular_sequencias(nums)

    entropia = calcular_entropia(nums)

    dispersao = float(np.std(nums))

    amplitude = max(nums) - min(nums)

    densidade = soma / 15


    # =====================================================
    # CLUSTER
    # =====================================================
    cluster_id = None
    cluster_similaridade = 0.0

    if cluster:

        cluster_id = cluster.get(
            "cluster_id"
        )

        cluster_similaridade = float(

            cluster.get(
                "similaridade_media",
                0
            )
        )


    # =====================================================
    # MONTE CARLO
    # =====================================================
    score_probabilistico = 0.0

    if montecarlo:

        score_probabilistico = float(

            montecarlo.get(
                "score_probabilistico",
                0
            )
        )


    # =====================================================
    # RESULTADO
    # =====================================================
    return {

        "pares": pares,

        "impares": impares,

        "primos": primos,

        "moldura": moldura,

        "soma": soma,

        "repetidos": repetidos,

        "linhas": linhas,

        "colunas": colunas,

        "quadrantes": quadrantes,

        "seq_max": seq_max,

        "entropia": round(
            entropia,
            6
        ),

        "dispersao": round(
            dispersao,
            6
        ),

        "amplitude": amplitude,

        "densidade": round(
            densidade,
            6
        ),

        "cluster_id": cluster_id,

        "cluster_similaridade": round(
            cluster_similaridade,
            6
        ),

        "score_probabilistico": round(
            score_probabilistico,
            10
        )
    }
