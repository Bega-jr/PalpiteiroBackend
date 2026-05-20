import numpy as np


# =========================================================
# DISTÂNCIA
# =========================================================
def distancia_jaccard(a, b):

    a = set(a)
    b = set(b)

    inter = len(a & b)
    uniao = len(a | b)

    if uniao == 0:
        return 0.0

    return 1 - (inter / uniao)


def distancia_hamming(a, b):

    a = sorted(a)
    b = sorted(b)

    return sum(

        1

        for x, y in zip(a, b)

        if x != y
    )


# =========================================================
# DIVERSIDADE
# =========================================================
def diversidade_basica_ok(
    novo,
    lista,
    minimo=9
):

    return all(

        len(
            set(novo)
            ^
            set(x["nums"])
        ) >= minimo

        for x in lista
    )


def diversidade_estrutural_ok(
    estrutura_nova,
    estruturas_existentes
):

    estrutura_id = tuple(
        estrutura_nova["linhas"]
    )

    return (
        estrutura_id
        not in estruturas_existentes
    )


def diversidade_estatistica_ok(
    features,
    lista_features,
    tolerancia_soma=12,
    tolerancia_pares=2
):

    for f in lista_features:

        if (

            abs(
                features["soma"]
                - f["soma"]
            ) <= tolerancia_soma

            and

            abs(
                features["pares"]
                - f["pares"]
            ) <= tolerancia_pares
        ):

            return False

    return True


# =========================================================
# DIVERSIDADE AVANÇADA
# =========================================================
def diversidade_avancada_ok(
    novo_jogo,
    candidatos,
    estrutura=None,
    minimo_jaccard=0.60,
    minimo_hamming=9
):

    if not candidatos:
        return True

    for candidato in candidatos:

        jogo_ref = candidato["nums"]

        dist_jaccard = distancia_jaccard(
            novo_jogo,
            jogo_ref
        )

        dist_hamming = distancia_hamming(
            novo_jogo,
            jogo_ref
        )

        # =====================================
        # MUITO PARECIDO
        # =====================================
        if dist_jaccard < minimo_jaccard:
            return False

        if dist_hamming < minimo_hamming:
            return False

        # =====================================
        # ESTRUTURA IGUAL
        # =====================================
        if estrutura:

            estrutura_ref = candidato.get(
                "estrutura",
                {}
            )

            if estrutura_ref:

                if (

                    estrutura["linhas"]

                    ==

                    estrutura_ref.get(
                        "linhas",
                        []
                    )
                ):

                    return False

    return True


# =========================================================
# SCORE DE DIVERSIDADE
# =========================================================
def score_diversidade(
    jogo,
    candidatos
):

    if not candidatos:
        return 1.0

    distancias = []

    for c in candidatos:

        dist = distancia_jaccard(
            jogo,
            c["nums"]
        )

        distancias.append(dist)

    media = float(
        np.mean(distancias)
    )

    return round(

        1.0 + (media * 0.08),

        6
    )
