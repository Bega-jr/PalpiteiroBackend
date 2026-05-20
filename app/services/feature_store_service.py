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

    seq = 1
    atual = 1

    nums = sorted(nums)

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


def calcular_quadrantes(nums):

    q1 = sum(1 for n in nums if n <= 7)

    q2 = sum(1 for n in nums if 8 <= n <= 13)

    q3 = sum(1 for n in nums if 14 <= n <= 19)

    q4 = sum(1 for n in nums if n >= 20)

    return [q1, q2, q3, q4]


# =========================================================
# FEATURE STORE PRINCIPAL
# =========================================================
def gerar_features_jogo(
    jogo,
    filtros=None,
    contexto=None,
    ultimo=None
):

    nums = sorted(jogo)

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

    elif filtros:

        repetidos = filtros.get(
            "repetidos",
            0
        )

    linhas = calcular_linhas(nums)

    colunas = calcular_colunas(nums)

    quadrantes = calcular_quadrantes(nums)

    seq_max = calcular_sequencias(nums)

    entropia = calcular_entropia(nums)

    dispersao = float(np.std(nums))

    amplitude = max(nums) - min(nums)

    densidade = soma / 15


    # =====================================================
    # CONTEXTO
    # =====================================================
    contexto = contexto or {}

    media_repetidos = contexto.get(
        "media_repetidos",
        0
    )

    media_soma = contexto.get(
        "media_soma",
        0
    )

    media_seq = contexto.get(
        "media_seq",
        0
    )


    # =====================================================
    # FEATURES FINAIS
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

        # =========================================
        # CONTEXTUAIS
        # =========================================
        "contexto_repetidos": round(
            media_repetidos,
            4
        ),

        "contexto_soma": round(
            media_soma,
            4
        ),

        "contexto_seq": round(
            media_seq,
            4
        )
    }


# =========================================================
# COMPATIBILIDADE LEGADA
# =========================================================
extrair_features = gerar_features_jogo
