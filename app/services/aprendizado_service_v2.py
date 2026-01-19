from app.services.supabase_service import get_supabase
from typing import Dict

PENALIDADE_MAX = 0.30  # até -30% no score
FATOR_MINIMO = 0.70   # nunca penaliza além disso


def obter_penalidades_por_numero(ano: int = 2026) -> Dict[int, float]:
    """
    Penaliza números que aparecem em palpites
    com baixo desempenho histórico.
    Retorna: {numero: fator}
    """

    supabase = get_supabase()

    dados = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            """
            numeros,
            acertos_11,
            acertos_12,
            acertos_13,
            acertos_14,
            acertos_15,
            total_concursos
            """
        )
        .gte("ano", ano)
        .execute()
    ).data or []

    if not dados:
        return {}

    falhas_por_numero = {n: 0 for n in range(1, 26)}

    for r in dados:
        numeros = r.get("numeros") or []

        impacto = (
            r["acertos_15"] * 1.0 +
            r["acertos_14"] * 0.6 +
            r["acertos_13"] * 0.3 +
            r["acertos_12"] * 0.1
        )

        falha = max(0, r["total_concursos"] - impacto)

        for n in numeros:
            falhas_por_numero[n] += falha

    max_falha = max(falhas_por_numero.values()) or 1

    penalidades = {}
    for n, f in falhas_por_numero.items():
        fator = 1 - (f / max_falha) * PENALIDADE_MAX
        penalidades[n] = round(max(FATOR_MINIMO, fator), 3)

    return penalidades
