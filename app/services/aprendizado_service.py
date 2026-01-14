from app.services.supabase_service import get_supabase

PENALIDADE_MAX = 0.25  # até -25% no score

def obter_penalidades_por_numero(ano: int = 2026):
    """
    Retorna um dict:
    { numero: fator_multiplicador }
    Ex: 0.85 = penalidade leve
    """
    supabase = get_supabase()

    dados = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            "acertos_11, acertos_12, acertos_13, "
            "acertos_14, acertos_15, total_concursos"
        )
        .gte("concurso_inicio", 3576)  # início de 2026
        .execute()
    ).data or []

    if not dados:
        return {}

    desempenho = {}
    total_registros = len(dados)

    for r in dados:
        impacto = (
            r["acertos_15"] * 1.0 +
            r["acertos_14"] * 0.6 +
            r["acertos_13"] * 0.3 +
            r["acertos_12"] * 0.1
        )

        # quanto mais concursos sem impacto, maior a penalidade
        falha = max(0, r["total_concursos"] - impacto)

        for n in range(1, 26):
            desempenho.setdefault(n, 0)
            desempenho[n] += falha

    penalidades = {}
    max_falha = max(desempenho.values()) or 1

    for n, f in desempenho.items():
        fator = 1 - (f / max_falha) * PENALIDADE_MAX
        penalidades[n] = round(max(0.75, fator), 3)

    return penalidades
