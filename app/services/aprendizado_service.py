from app.services.supabase_service import get_supabase

PENALIDADE_PADRAO_MAX = 0.35  # até -35%

def obter_penalidade_por_padrao(ano: int = 2026):
    """
    Retorna fatores multiplicadores por padrão:
    soma, pares, primos, sequencia
    """

    supabase = get_supabase()

    dados = (
        supabase
        .table("lotofacil_concursos")
        .select("dezenas")
        .gte("concurso", 3576)
        .execute()
    ).data or []

    if not dados:
        return {}

    stats = {
        "soma": [],
        "pares": [],
        "primos": [],
        "seq": [],
    }

    PRIMOS = {2,3,5,7,11,13,17,19,23}

    for r in dados:
        nums = sorted(map(int, r["dezenas"]))
        stats["soma"].append(sum(nums))
        stats["pares"].append(sum(1 for n in nums if n % 2 == 0))
        stats["primos"].append(sum(1 for n in nums if n in PRIMOS))

        seq = atual = 1
        for i in range(1, len(nums)):
            if nums[i] == nums[i - 1] + 1:
                atual += 1
                seq = max(seq, atual)
            else:
                atual = 1
        stats["seq"].append(seq)

    def fator(valor, media, desvio):
        if desvio == 0:
            return 1.0
        z = abs(valor - media) / desvio
        penal = min(z / 3, 1) * PENALIDADE_PADRAO_MAX
        return round(max(0.65, 1 - penal), 3)

    import statistics

    medias = {k: statistics.mean(v) for k, v in stats.items()}
    desvios = {k: statistics.pstdev(v) for k, v in stats.items()}

    return {
        "medias": medias,
        "desvios": desvios,
        "fator": fator
    }
