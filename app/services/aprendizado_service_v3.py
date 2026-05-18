from typing import Dict

from app.services.supabase_service import get_supabase


# ==================================================
# LIMITES DE SEGURANÇA
# ==================================================
PENALIDADE_MAX = 0.25
FATOR_MINIMO = 0.75
FATOR_MAXIMO = 1.08


# ==================================================
# PESOS DE PERFORMANCE
# ==================================================
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00


# ==================================================
# BONUS DE REGIME
# ==================================================
BONUS_REGIME = {
    "EXPANSAO_QUENTES": 1.00,
    "NEUTRO": 1.02,
    "CONTRACAO_FRIAS": 1.05
}


# ==================================================
# BASE HISTÓRICA (SEU MÉTODO ATUAL)
# ==================================================
def calcular_fator_base(
    ano: int = 2026
):

    supabase = get_supabase()

    res = (
        supabase
        .table(
            "palpites_resultados_reais"
        )
        .select("""
            qtd_palpites,
            acertos_11,
            acertos_12,
            acertos_13,
            acertos_14,
            acertos_15
        """)
        .gte(
            "data_referencia",
            f"{ano}-01-01"
        )
        .lte(
            "data_referencia",
            f"{ano}-12-31"
        )
        .execute()
    )

    if not res.data:

        return {
            "fator": 1.0,
            "eficiencia": 0.0,
            "impacto": 0.0,
            "total_palpites": 0
        }

    impacto_total = 0.0
    total_palpites = 0

    for r in res.data:

        impacto = (

            r.get("acertos_11", 0) * PESO_11 +
            r.get("acertos_12", 0) * PESO_12 +
            r.get("acertos_13", 0) * PESO_13 +
            r.get("acertos_14", 0) * PESO_14 +
            r.get("acertos_15", 0) * PESO_15
        )

        impacto_total += impacto

        total_palpites += r.get(
            "qtd_palpites",
            0
        )

    eficiencia = (

        impacto_total / total_palpites

        if total_palpites > 0
        else 0.0
    )

    penalidade = min(

        PENALIDADE_MAX,

        (1 - eficiencia)
        *
        PENALIDADE_MAX
    )

    fator = max(

        FATOR_MINIMO,

        1 - penalidade
    )

    return {
        "fator": round(fator, 4),
        "eficiencia": round(eficiencia, 4),
        "impacto": round(impacto_total, 4),
        "total_palpites": total_palpites
    }


# ==================================================
# NOVO BONUS TELEMETRIA
# ==================================================
def obter_bonus_telemetria():

    supabase = get_supabase()

    try:

        dados = (

            supabase
            .table(
                "telemetria_geracao"
            )
            .select(
                "regime,score_top1"
            )
            .order(
                "created_at",
                desc=True
            )
            .limit(20)
            .execute()
            .data
        )

        if not dados:
            return 1.0

        score_medio = 0
        qtd = 0

        bonus_regime = 1.0

        for row in dados:

            if row.get("score_top1"):

                score_medio += float(
                    row["score_top1"]
                )

                qtd += 1

            regime = row.get(
                "regime"
            )

            if regime in BONUS_REGIME:

                bonus_regime *= BONUS_REGIME[
                    regime
                ]

        if qtd > 0:

            score_medio = (
                score_medio / qtd
            )

        else:

            score_medio = 0.40

        # score médio forte
        bonus_score = 1.0

        if score_medio >= 0.42:
            bonus_score = 1.02

        elif score_medio < 0.39:
            bonus_score = 0.98

        bonus_regime = min(
            1.05,
            bonus_regime
        )

        return round(
            bonus_regime * bonus_score,
            4
        )

    except:

        return 1.0


# ==================================================
# MÉTODO PRINCIPAL
# ==================================================
def obter_fator_aprendizado_global(
    ano: int = 2026
) -> Dict[str, float]:

    base = calcular_fator_base(
        ano
    )

    bonus_telemetria = (
        obter_bonus_telemetria()
    )

    fator_final = (
        base["fator"]
        *
        bonus_telemetria
    )

    fator_final = max(
        FATOR_MINIMO,
        min(
            FATOR_MAXIMO,
            fator_final
        )
    )

    return {

        "fator":
            round(
                fator_final,
                4
            ),

        "fator_base":
            base["fator"],

        "bonus_telemetria":
            bonus_telemetria,

        "eficiencia":
            base["eficiencia"],

        "impacto":
            base["impacto"],

        "total_palpites":
            base["total_palpites"]
    }


# ==================================================
# APLICAÇÃO
# ==================================================
def aplicar_fator_aprendizado(
    score: float,
    fator: float
):

    if fator <= 0:
        fator = 1.0

    return round(
        score * fator,
        6
    )


# ==================================================
# DEBUG HUMANO
# ==================================================
def interpretar_fator(
    dados: Dict[str, float]
):

    fator = dados.get(
        "fator",
        1.0
    )

    if fator >= 0.98:
        return "🔥 sistema otimizado"

    elif fator >= 0.90:
        return "🟢 sistema estável"

    elif fator >= 0.82:
        return "🟡 ajuste em andamento"

    else:
        return "🔴 sistema em correção"
