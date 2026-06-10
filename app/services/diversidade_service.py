import numpy as np


# =========================================================
# HELPERS
# =========================================================
def similaridade_jogos(a, b):

    return len(
        set(a) & set(b)
    )


def distancia_linhas(l1, l2):

    return sum(

        abs(a - b)

        for a, b in zip(l1, l2)
    )


# =========================================================
# DIVERSIDADE AVANÇADA
# =========================================================
def diversidade_avancada_ok(
    jogo,
    candidatos,
    estrutura=None,
    cluster_id=None,
    limite_similares=10,
    limite_cluster=8,
    **kwargs
):

    # =====================================================
    # SEM CANDIDATOS
    # =====================================================
    if not candidatos:
        return True

    similares_cluster = 0

    for c in candidatos:

        nums_ref = c.get(
            "nums",
            []
        )

        # =================================================
        # OVERLAP
        # =================================================
        overlap = similaridade_jogos(
            jogo,
            nums_ref
        )

        if overlap >= limite_similares:
            return False

        # =================================================
        # CLUSTER
        # =================================================
        if (

            cluster_id is not None

            and

            c.get("cluster_id") == cluster_id
        ):

            similares_cluster += 1

        # =================================================
        # LINHAS
        # =================================================
        if estrutura:

            linhas_ref = (
                c.get("estrutura", {})
                .get("linhas", [])
            )

            if linhas_ref:

                dist = distancia_linhas(

                    estrutura["linhas"],
                    linhas_ref
                )

                if dist <= 1:
                    return False

    # =====================================================
    # SATURAÇÃO DE CLUSTER
    # =====================================================
    if similares_cluster >= limite_cluster:
        return False

    return True
