from app.services.supabase_service import get_supabase

PREMIOS_FIXOS = {
    11: 6,
    12: 12,
    13: 30,
    14: 1500,
    15: 1500000
}

CUSTO_JOGO = 3.0


def obter_probabilidades_reais(versao="v4-roi-inteligente"):
    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
        .select("*")
        .eq("versao_gerador", versao)
        .order("data_referencia", desc=True)
        .limit(50)
        .execute()
    )

    if not res.data:
        return None

    total_palpites = sum(r["qtd_palpites"] for r in res.data)

    if total_palpites == 0:
        return None

    probs = {}

    for faixa in [11, 12, 13, 14, 15]:
        total_acertos = sum(r.get(f"acertos_{faixa}", 0) for r in res.data)
        probs[faixa] = total_acertos / total_palpites

    return probs


def calcular_roi_real(score, probs):
    """
    ROI usando probabilidade REAL do sistema
    """

    if not probs:
        return 0  # fallback neutro

    retorno = 0

    for faixa in probs:
        retorno += probs[faixa] * PREMIOS_FIXOS[faixa]

    roi = (retorno - CUSTO_JOGO) / CUSTO_JOGO

    # pondera pelo score do palpite
    roi_final = roi * (0.5 + score)

    return round(roi_final, 4)
