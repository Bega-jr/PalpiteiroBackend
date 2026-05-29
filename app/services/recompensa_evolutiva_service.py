from collections import defaultdict

historico_clusters = defaultdict(int)


def calcular_recompensa_evolutiva(
    estrutura,
    filtros,
    cluster_id
):

    recompensa = 1.0

    # ==========================================
    # SOMA
    # ==========================================
    soma = filtros["soma"]

    if 180 <= soma <= 210:
        recompensa *= 1.03

    elif soma < 165:
        recompensa *= 0.96

    elif soma > 225:
        recompensa *= 0.95


    # ==========================================
    # PARES
    # ==========================================
    pares = filtros["pares"]

    if 6 <= pares <= 9:
        recompensa *= 1.02
    else:
        recompensa *= 0.97


    # ==========================================
    # PRIMOS
    # ==========================================
    primos = filtros["primos"]

    if 4 <= primos <= 6:
        recompensa *= 1.015


    # ==========================================
    # SEQUÊNCIA
    # ==========================================
    if filtros["seq_max"] >= 5:
        recompensa *= 0.93


    # ==========================================
    # CLUSTER
    # ==========================================
    historico_clusters[cluster_id] += 1

    uso_cluster = historico_clusters[cluster_id]

    if uso_cluster <= 8:
        recompensa *= 1.04

    elif uso_cluster >= 25:
        recompensa *= 0.94


    # ==========================================
    # LINHAS
    # ==========================================
    linhas = estrutura["linhas"]

    if max(linhas) <= 4:
        recompensa *= 1.03

    if min(linhas) == 0:
        recompensa *= 0.92


    return round(recompensa, 6)
