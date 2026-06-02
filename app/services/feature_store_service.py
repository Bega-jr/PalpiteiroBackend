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
# FEATURE STORE
# =========================================================
def gerar_features_jogo(
    jogo,
    ultimo=None,
    filtros=None,
    estrutura=None,
    contexto=None,
    **kwargs
):

    nums = sorted(jogo)

    # =====================================================
    # FALLBACKS & VALIDAÇÕES (Dicionários Principais)
    # =====================================================
    if filtros is None:
        filtros = {}

    if estrutura is None:
        estrutura = {}

    if contexto is None:
        contexto = {}

    # =====================================================
    # GARANTIA DE CHAVES (Preenche individualmente se faltar)
    # =====================================================
    if "pares" not in filtros:
        filtros["pares"] = sum(1 for n in nums if n % 2 == 0)

    if "impares" not in filtros:
        filtros["impares"] = 15 - filtros["pares"]

    if "primos" not in filtros:
        filtros["primos"] = sum(1 for n in nums if n in PRIMOS)

    if "moldura" not in filtros:
        filtros["moldura"] = sum(1 for n in nums if n in MOLDURA)

    if "soma" not in filtros:
        filtros["soma"] = sum(nums)

    if "repetidos" not in filtros:
        filtros["repetidos"] = (
            len(set(nums) & set(ultimo))
            if ultimo
            else 0
        )

    if "seq_max" not in filtros:
        filtros["seq_max"] = calcular_sequencias(nums)

    if "linhas" not in estrutura:
        estrutura["linhas"] = calcular_linhas(nums)

    # =====================================================
    # FEATURES (Identação Corrigida para Fora dos IFs)
    # =====================================================
    colunas = calcular_colunas(nums)
    quadrantes = calcular_quadrantes(nums)
    entropia = calcular_entropia(nums)
    dispersao = float(np.std(nums))
    amplitude = max(nums) - min(nums)
    densidade = filtros["soma"] / 15

    features = {

        # =========================================
        # BASE
        # =========================================
        "pares": filtros["pares"],

        "impares": filtros["impares"],

        "primos": filtros["primos"],

        "moldura": filtros["moldura"],

        "soma": filtros["soma"],

        "repetidos": filtros["repetidos"],

        "seq_max": filtros["seq_max"],


        # =========================================
        # ESTRUTURA
        # =========================================
        "linhas": estrutura["linhas"],

        "colunas": colunas,

        "quadrantes": quadrantes,


        # =========================================
        # ESTATÍSTICAS
        # =========================================
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
        # CONTEXTO
        # =========================================
        "contexto_media_repetidos":
            contexto.get(
                "media_repetidos",
                0.0
            ),

        "contexto_media_soma":
            contexto.get(
                "media_soma",
                0.0
            ),

        "contexto_media_seq":
            contexto.get(
                "media_seq",
                0.0
            )
    }

    return features


# =========================================================
# COMPATIBILIDADE RETROATIVA
# =========================================================
extrair_features = gerar_features_jogo

