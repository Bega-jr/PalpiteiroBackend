from app.services.supabase_service import get_supabase
from typing import Dict

# --------------------------------------------------
# Limites de segurança
# --------------------------------------------------
PENALIDADE_MAX = 0.25   # até -25%
FATOR_MINIMO = 0.75    # nunca abaixo disso

# Pesos por faixa de acerto
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00


def obter_fator_aprendizado_global(ano: int = 2026) -> Dict[str, float]:
    """
    Aprendizado V3
    Calcula um fator GLOBAL baseado na performance REAL do gerador.
    NÃO penaliza números individuais.
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            """
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
        return {
            "fator": 1.0,
            "eficiencia": 0.0
        }

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
        eficiencia = 0.0
    else:
        eficiencia = impacto_total / total_palpites

    penalidade = min(PENALIDADE_MAX, (1 - eficiencia) * PENALIDADE_MAX)
    fator = max(FATOR_MINIMO, 1 - penalidade)

    return {
        "fator": round(fator, 4),
        "eficiencia": round(eficiencia, 4)
    }


def aplicar_fator_aprendizado(score: float, fator: float) -> float:
    """
    Aplicação segura do aprendizado
    """
    return round(score * fator, 6)
