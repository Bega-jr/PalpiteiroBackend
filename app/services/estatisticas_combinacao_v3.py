from app.services.supabase_service import get_supabase
from collections import defaultdict
from typing import Dict, Tuple
import json


# ======================================================
# Pesos por faixa de acerto
# ======================================================
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00


# ======================================================
# Métricas estruturais
# ======================================================
def extrair_metricas_jogo(nums):
    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})

    linhas = (
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    )

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "linhas": linhas
    }


# ======================================================
# Score REAL por combinação estrutural (CORRETO)
# ======================================================
def calcular_score_combinacoes_reais(
    ano: int = 2026
) -> Dict[Tuple, float]:
    """
    Aprende score estrutural REAL a partir de palpites
    já conferidos individualmente
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_validos")
        .select(
            """
            numeros,
            acertos
            """
        )
        .gte("data_referencia", f"{ano}-01-01")
        .lte("data_referencia", f"{ano}-12-31")
        .execute()
    )

    if not res.data:
        return {}

    scores = defaultdict(float)
    ocorrencias = defaultdict(int)

    for r in res.data:
        if r["acertos"] < 11:
            continue

        nums = json.loads(r["numeros"])
        m = extrair_metricas_jogo(nums)

        impacto = (
            (1 if r["acertos"] == 11 else 0) * PESO_11 +
            (1 if r["acertos"] == 12 else 0) * PESO_12 +
            (1 if r["acertos"] == 13 else 0) * PESO_13 +
            (1 if r["acertos"] == 14 else 0) * PESO_14 +
            (1 if r["acertos"] == 15 else 0) * PESO_15
        )

        chave = (
            round(m["soma"] / 10) * 10,
            m["pares"],
            m["primos"],
            m["linhas"]
        )

        scores[chave] += impacto
        ocorrencias[chave] += 1

    return {
        k: round(scores[k] / ocorrencias[k], 6)
        for k in scores
    }


# ======================================================
# BACKWARD COMPATIBILITY
# ======================================================
calcular_score_combinacoes = calcular_score_combinacoes_reais

