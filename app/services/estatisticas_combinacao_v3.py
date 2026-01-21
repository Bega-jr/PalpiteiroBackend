from app.services.supabase_service import get_supabase
from collections import defaultdict
from typing import Dict, Tuple


# ======================================================
# Configurações
# ======================================================
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00


# ======================================================
# Métricas estruturais do jogo
# ======================================================
def extrair_metricas_jogo(nums):
    """
    Extrai métricas estruturais de um jogo Lotofácil
    """
    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in {2, 3, 5, 7, 11, 13, 17, 19, 23})

    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]

    return {
        "soma": soma,
        "pares": pares,
        "primos": primos,
        "linhas": tuple(linhas)
    }


# ======================================================
# Score histórico por combinação estrutural
# ======================================================
def calcular_score_combinacoes(
    ano: int = 2026
) -> Dict[Tuple, float]:
    """
    Calcula score histórico REAL das combinações estruturais
    usando palpites_resultados_reais

    Chave:
    (soma_aproximada, pares, primos, linhas)
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            """
            soma,
            pares,
            primos,
            linhas,
            acertos_11,
            acertos_12,
            acertos_13,
            acertos_14,
            acertos_15
            """
        )
        .gte("data_referencia", f"{ano}-01-01")
        .lte("data_referencia", f"{ano}-12-31")
        .execute()
    )

    scores = defaultdict(float)
    ocorrencias = defaultdict(int)

    if not res.data:
        return {}

    for r in res.data:
        impacto = (
            r["acertos_11"] * PESO_11 +
            r["acertos_12"] * PESO_12 +
            r["acertos_13"] * PESO_13 +
            r["acertos_14"] * PESO_14 +
            r["acertos_15"] * PESO_15
        )

        chave = (
            round(r["soma"] / 10) * 10,
            r["pares"],
            r["primos"],
            tuple(r["linhas"])
        )

        scores[chave] += impacto
        ocorrencias[chave] += 1

    # Normalização segura
    score_final = {}
    for k in scores:
        score_final[k] = round(scores[k] / ocorrencias[k], 6)

    return score_final

