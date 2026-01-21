from app.services.supabase_service import get_supabase
from typing import Dict

PENALIDADE_MAX = 0.30   # até -30% no score
FATOR_MINIMO = 0.70    # nunca penaliza além disso


def obter_penalidades_por_numero(ano: int = 2026) -> Dict[int, float]:
    """
    Calcula penalidade baseada na performance REAL dos palpites do sistema.
    Usa apenas a tabela palpites_resultados_reais (dados consolidados).
    Retorna um fator multiplicador por número (1 a 25).
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            "acertos_11, acertos_12, acertos_13, acertos_14, acertos_15, qtd_palpites"
        )
        .gte("data_referencia", f"{ano}-01-01")
        .lte("data_referencia", f"{ano}-12-31")
        .execute()
    )

    if not res.data:
        # Nenhum dado real ainda → sem penalidade
        return {n: 1.0 for n in range(1, 26)}

    # -----------------------------
    # Cálculo de falha global
    # -----------------------------
    falha_total = 0.0

    for r in res.data:
        impacto = (
            r["acertos_15"] * 1.0 +
            r["acertos_14"] * 0.6 +
            r["acertos_13"] * 0.3 +
            r["acertos_12"] * 0.1
        )

        falha = max(0, r["qtd_palpites"] - impacto)
        falha_total += falha

    # Normalização segura
    max_falha = falha_total if falha_total > 0 else 1.0
    fator_global = 1 - min(PENALIDADE_MAX, falha_total / max_falha * PENALIDADE_MAX)
    fator_global = max(FATOR_MINIMO, fator_global)

    # -----------------------------
    # Aplica fator global a todos
    # (números individuais são
    # tratados no score estatístico)
    # -----------------------------
    penalidades = {
        n: round(fator_global, 3)
        for n in range(1, 26)
    }

    return penalidades

