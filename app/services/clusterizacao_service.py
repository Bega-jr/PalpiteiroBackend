import numpy as np


# =========================================================
# HELPERS
# =========================================================
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
# CLUSTERIZAÇÃO
# =========================================================
def identificar_cluster_jogo(
    dados,
    **kwargs
):

    # =====================================================
    # CASO RECEBA FEATURES
    # =====================================================
    if isinstance(dados, dict):

        pares = dados.get("pares", 0)

        primos = dados.get("primos", 0)

        soma = dados.get("soma", 0)

        seq = dados.get("seq_max", 0)

        entropia = dados.get("entropia", 0)

        dispersao = dados.get("dispersao", 0)

        linhas = dados.get(
            "linhas",
            [0, 0, 0, 0, 0]
        )

    # =====================================================
    # CASO RECEBA JOGO
    # =====================================================
    else:

        nums = sorted([
            int(n)
            for n in dados
        ])

        pares = sum(
            1 for n in nums
            if n % 2 == 0
        )

        primos = sum(
            1 for n in nums
            if n in {
                2, 3, 5, 7, 11,
                13, 17, 19, 23
            }
        )

        soma = sum(nums)

        seq = max(np.diff(nums)) \
            if len(nums) > 1 \
            else 0

        entropia = float(
            np.std(nums)
        )

        dispersao = float(
            max(nums) - min(nums)
        )

        linhas = calcular_linhas(nums)

    # =====================================================
    # SCORE VETORIAL
    # =====================================================
    vetor = [

        pares,

        primos,

        soma / 15,

        seq,

        entropia,

        dispersao,

        max(linhas)
    ]

    # =====================================================
    # CLUSTER SIMPLIFICADO
    # =====================================================
    assinatura = int(

        sum(vetor) * 1000

    ) % 12

    return assinatura
