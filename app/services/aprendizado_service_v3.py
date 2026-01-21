# app/services/aprendizado_service_v3.py

from app.services.supabase_service import get_supabase
from typing import Dict, Tuple
from collections import defaultdict

# ======================================================
# Configurações globais
# ======================================================
PENALIDADE_MAX = 0.25   # até -25%
FATOR_MINIMO = 0.75    # nunca abaixo disso
FATOR_MAXIMO = 1.25    # nunca acima disso

# Pesos por faixa de acerto
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00


# ======================================================
# Aprendizado GLOBAL por eficiência real
# ======================================================
def obter_fator_aprendizado_global(ano: int = 2026) -> Dict[str, float]:
    """
    Calcula fator global baseado na eficiência REAL
    da tabela palpites_resultados_reais.

    Retorna:
    {
        "fator": float,
        "eficiencia": float
    }
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            """
            data_referencia,
            qtd_palpites,
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

    if not res.data:
        return {"fator": 1.0, "eficiencia": 0.0}

    impacto_total = 0.0
    total_palpites = 0

    for r in res.data:
        impacto = (
            r["acertos_11"] * PESO_11 +
            r["acertos_12"] * PESO_12 +
            r["acertos_13"] * PESO_13 +
            r["acertos_14"] * PESO_14 +
            r["acertos_15"] * PESO_15
        )

        impacto_total += impacto
        total_palpites += r["qtd_palpites"]

    if total_palpites == 0:
        return {"fator": 1.0, "eficiencia": 0.0}

    eficiencia = impacto_total / total_palpites

    penalidade = min(PENALIDADE_MAX, (1 - eficiencia) * PENALIDADE_MAX)
    fator = max(FATOR_MINIMO, 1 - penalidade)

    return {
        "fator": round(fator, 4),
        "eficiencia": round(eficiencia, 4)
    }


# ======================================================
# Aprendizado POR NÚMERO (v3)
# ======================================================
def obter_fator_aprendizado_por_numero(
    ano: int = 2026
) -> Dict[int, float]:
    """
    Calcula fator individual por número (1–25),
    baseado em desempenho real (acertos 11–15).

    Retorna:
    { numero: fator }
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
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

    score_numero = defaultdict(float)
    aparicoes = defaultdict(int)

    pesos = {
        11: PESO_11,
        12: PESO_12,
        13: PESO_13,
        14: PESO_14,
        15: PESO_15
    }

    for r in res.data:
        acertos = r.get("acertos", 0)
        peso = pesos.get(acertos, 0)

        if peso <= 0:
            continue

        for n in r["numeros"]:
            score_numero[n] += peso
            aparicoes[n] += 1

    if not score_numero:
        return {}

    medias = [
        score_numero[n] / aparicoes[n]
        for n in score_numero
        if aparicoes[n] > 0
    ]

    media_global = sum(medias) / len(medias)

    fatores = {}
    for n in score_numero:
        fator = (score_numero[n] / aparicoes[n]) / media_global

        if fator < FATOR_MINIMO:
            fator = FATOR_MINIMO
        elif fator > FATOR_MAXIMO:
            fator = FATOR_MAXIMO

        fatores[n] = round(fator, 4)

    return fatores


# ======================================================
# Aplicação segura do aprendizado
# ======================================================
def aplicar_fator_aprendizado(
    score_base: float,
    fator_aprendizado: float
) -> float:
    """
    Aplica aprendizado de forma controlada
    """
    return round(score_base * fator_aprendizado, 6)

