import math
import numpy as np

from datetime import datetime

from app.services.supabase_service import (
    get_supabase
)


# =========================================================
# CONFIG
# =========================================================
MIN_CONCURSOS = 15

VERSAO = "v1.0-auto-evolution"


# =========================================================
# HELPERS
# =========================================================
def media_segura(v, fallback=0.0):

    vals = [

        float(x)

        for x in v

        if x is not None
    ]

    if not vals:
        return fallback

    return float(np.mean(vals))


def limitar(

    valor,

    minimo,

    maximo
):

    return max(
        minimo,
        min(valor, maximo)
    )


# =========================================================
# ESTABILIDADE
# =========================================================
def calcular_estabilidade(acertos):

    if len(acertos) <= 1:
        return 0.5

    desvio = np.std(acertos)

    estabilidade = 1 / (
        1 + desvio
    )

    return round(
        float(estabilidade),
        6
    )


# =========================================================
# DIVERSIDADE
# =========================================================
def calcular_diversidade(clusters):

    if not clusters:
        return 0.0

    unicos = len(
        set(clusters)
    )

    total = len(clusters)

    return round(
        unicos / total,
        6
    )


# =========================================================
# REWARD CENTRAL
# =========================================================
def calcular_reward_global(

    media_acertos,

    taxa_14,

    diversidade,

    estabilidade,

    score_mc,

    score_estrutural
):

    reward = (

        media_acertos * 0.35

        +

        taxa_14 * 0.20

        +

        diversidade * 0.15

        +

        estabilidade * 0.10

        +

        score_mc * 0.10

        +

        score_estrutural * 0.10
    )

    return round(
        float(reward),
        6
    )


# =========================================================
# AJUSTE PESOS
# =========================================================
def gerar_configuracao_dinamica(

    reward,

    diversidade,

    estabilidade,

    taxa_14
):

    # =====================================================
    # BASE
    # =====================================================
    peso_base = 0.40

    peso_feedback = 0.10

    peso_regime = 0.10

    peso_exploracao = 0.12

    peso_mutacao = 0.08

    peso_diversidade = 0.10

    temperatura_ia = 1.00


    # =====================================================
    # SISTEMA EVOLUTIVO
    # =====================================================

    # BAIXA PERFORMANCE
    if reward < 5.0:

        peso_exploracao += 0.08

        peso_mutacao += 0.05

        temperatura_ia += 0.12

        peso_base -= 0.05


    # COLAPSO DE DIVERSIDADE
    if diversidade < 0.45:

        peso_diversidade += 0.08

        peso_exploracao += 0.04

        temperatura_ia += 0.08


    # INSTABILIDADE
    if estabilidade < 0.40:

        peso_feedback += 0.04

        peso_regime += 0.03


    # REGIME MUITO FORTE
    if taxa_14 >= 0.25:

        peso_base += 0.04

        temperatura_ia -= 0.05


    # =====================================================
    # NORMALIZA
    # =====================================================
    peso_base = limitar(
        peso_base,
        0.20,
        0.60
    )

    peso_feedback = limitar(
        peso_feedback,
        0.05,
        0.30
    )

    peso_regime = limitar(
        peso_regime,
        0.05,
        0.30
    )

    peso_exploracao = limitar(
        peso_exploracao,
        0.05,
        0.30
    )

    peso_mutacao = limitar(
        peso_mutacao,
        0.03,
        0.25
    )

    peso_diversidade = limitar(
        peso_diversidade,
        0.05,
        0.30
    )

    temperatura_ia = limitar(
        temperatura_ia,
        0.85,
        1.30
    )

    return {

        "peso_base": round(
            peso_base,
            6
        ),

        "peso_feedback": round(
            peso_feedback,
            6
        ),

        "peso_regime": round(
            peso_regime,
            6
        ),

        "peso_exploracao": round(
            peso_exploracao,
            6
        ),

        "peso_mutacao": round(
            peso_mutacao,
            6
        ),

        "peso_diversidade": round(
            peso_diversidade,
            6
        ),

        "temperatura_ia": round(
            temperatura_ia,
            6
        )
    }


# =========================================================
# PROCESSAMENTO PRINCIPAL
# =========================================================
def processar_recompensa_evolutiva():

    supabase = get_supabase()

    print(
        f"🧠 Recompensa Evolutiva {VERSAO}"
    )


    # =====================================================
    # HISTÓRICO REAL
    # =====================================================
    rows = (

        supabase
        .table("palpites_resultados_reais")
        .select("*")
        .order(
            "concurso_referencia",
            desc=True
        )
        .limit(200)
        .execute()
        .data
    )

    if not rows:

        print(
            "⚠️ Sem histórico suficiente."
        )

        return


    # =====================================================
    # MÉTRICAS
    # =====================================================
    acertos = []

    hits14 = 0

    clusters = []

    scores_mc = []

    scores_estruturais = []


    for r in rows:

        acerto = int(
            r.get(
                "acertos",
                0
            )
        )

        acertos.append(
            acerto
        )

        if acerto >= 14:
            hits14 += 1


        cluster = r.get(
            "cluster_id"
        )

        if cluster is not None:

            clusters.append(
                cluster
            )


        score_mc = r.get(
            "score_montecarlo"
        )

        if score_mc is not None:

            scores_mc.append(
                float(score_mc)
            )


        score_est = r.get(
            "score_estrutural"
        )

        if score_est is not None:

            scores_estruturais.append(
                float(score_est)
            )


    # =====================================================
    # CÁLCULOS
    # =====================================================
    media_acertos = media_segura(
        acertos
    )

    taxa_14 = (

        hits14 / len(rows)

        if rows
        else 0
    )

    diversidade = calcular_diversidade(
        clusters
    )

    estabilidade = calcular_estabilidade(
        acertos
    )

    media_mc = media_segura(
        scores_mc,
        0.50
    )

    media_estrutural = media_segura(
        scores_estruturais,
        0.50
    )


    # =====================================================
    # REWARD
    # =====================================================
    reward = calcular_reward_global(

        media_acertos=media_acertos,

        taxa_14=taxa_14,

        diversidade=diversidade,

        estabilidade=estabilidade,

        score_mc=media_mc,

        score_estrutural=media_estrutural
    )


    # =====================================================
    # CONFIG DINÂMICA
    # =====================================================
    config = gerar_configuracao_dinamica(

        reward=reward,

        diversidade=diversidade,

        estabilidade=estabilidade,

        taxa_14=taxa_14
    )


    # =====================================================
    # LOG
    # =====================================================
    payload = {

        "reward_global": reward,

        "media_acertos": round(
            media_acertos,
            6
        ),

        "taxa_14": round(
            taxa_14,
            6
        ),

        "diversidade": round(
            diversidade,
            6
        ),

        "estabilidade": round(
            estabilidade,
            6
        ),

        "score_mc": round(
            media_mc,
            6
        ),

        "score_estrutural": round(
            media_estrutural,
            6
        ),

        "configuracao": config,

        "versao": VERSAO,

        "updated_at": datetime.now().isoformat()
    }


    # =====================================================
    # SALVA CONFIG
    # =====================================================
    try:

        supabase.table(
            "configuracao_dinamica_ia"
        ).upsert(

            {

                "id": 1,

                **config,

                "reward_global": reward,

                "updated_at": datetime.now().isoformat()
            },

            on_conflict="id"

        ).execute()


        supabase.table(
            "reward_evolutivo_logs"
        ).insert(
            payload
        ).execute()


        print(
            "✅ Configuração evolutiva atualizada."
        )

    except Exception as e:

        print(
            f"⚠️ Erro salvando reward: {e}"
        )


    # =====================================================
    # OUTPUT
    # =====================================================
    print()

    print(
        f"🎯 Reward Global: {reward}"
    )

    print(
        f"📈 Média Acertos: {media_acertos:.4f}"
    )

    print(
        f"💎 Taxa 14+: {taxa_14:.4f}"
    )

    print(
        f"🧬 Diversidade: {diversidade:.4f}"
    )

    print(
        f"🛡️ Estabilidade: {estabilidade:.4f}"
    )

    print()

    print(
        "⚙️ Configuração dinâmica:"
    )

    for k, v in config.items():

        print(
            f"   {k}: {v}"
        )


# =========================================================
# EXEC
# =========================================================
if __name__ == "__main__":

    processar_recompensa_evolutiva()
