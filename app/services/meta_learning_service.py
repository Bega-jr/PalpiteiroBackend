from typing import Dict

from app.services.supabase_service import get_supabase


# ==================================================
# DEFAULTS
# ==================================================
PESOS_DEFAULT = {
    "peso_base": 0.30,
    "peso_global": 0.15,
    "peso_feedback": 0.15,
    "peso_regime": 0.10,
    "peso_moldura": 0.10,
    "peso_estrutura": 0.10,
    "peso_fadiga": 0.05,
    "peso_recencia": 0.05
}


# ==================================================
# LEITURA DOS PESOS
# ==================================================
def obter_pesos_ensemble() -> Dict[str, float]:

    supabase = get_supabase()

    try:

        rows = (
            supabase
            .table("memoria_meta_learning")
            .select("*")
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
            .data
        )

        if not rows:
            return PESOS_DEFAULT.copy()

        row = rows[0]

        return {
            k: float(row.get(k, v))
            for k, v in PESOS_DEFAULT.items()
        }

    except Exception as e:

        print(
            f"⚠️ Erro ao ler pesos da memória: {e}"
        )

        return PESOS_DEFAULT.copy()


# ==================================================
# FEEDBACK + EVOLUÇÃO DOS PESOS
# ==================================================
def atualizar_meta_learning(
    media_acertos: float,
    concurso_ref: int,

    tipo_regime: str = "NEUTRO",
    fator_feedback: float = 1.0,
    fator_global: float = 1.0,

    melhor_acerto: int = 0,
    pior_acerto: int = 0,
    dispersao: int = 0,
    qtd_palpites: int = 7,
    score_estrutural: float = 0.0
):

    supabase = get_supabase()

    pesos = obter_pesos_ensemble()

    try:

        # ==========================================
        # AJUSTE POR MÉDIA
        # ==========================================
        if media_acertos < 9:

            pesos["peso_estrutura"] += 0.02
            pesos["peso_feedback"] += 0.02

            pesos["peso_base"] -= 0.03
            pesos["peso_regime"] -= 0.01

        elif media_acertos >= 11:

            pesos["peso_base"] += 0.02
            pesos["peso_regime"] += 0.01

            pesos["peso_estrutura"] -= 0.01
            pesos["peso_feedback"] -= 0.01


        # ==========================================
        # AJUSTE POR DISPERSÃO
        # (quanto mais inconsistente, mais valor estrutural)
        # ==========================================
        if dispersao >= 4:

            pesos["peso_estrutura"] += 0.01
            pesos["peso_fadiga"] += 0.01

            pesos["peso_base"] -= 0.01


        # ==========================================
        # AJUSTE POR REGIME
        # ==========================================
        if tipo_regime == "EXPANSAO_QUENTES":

            pesos["peso_regime"] += 0.01

        elif tipo_regime == "CONTRACAO_FRIAS":

            pesos["peso_recencia"] += 0.01


        # ==========================================
        # LIMITES
        # ==========================================
        for k in pesos:

            pesos[k] = max(
                0.02,
                min(
                    0.60,
                    pesos[k]
                )
            )


        # ==========================================
        # NORMALIZAÇÃO
        # ==========================================
        soma = sum(
            pesos.values()
        )

        chaves = list(
            pesos.keys()
        )

        for k in chaves:

            pesos[k] = round(
                pesos[k] / soma,
                4
            )


        diferenca = round(
            1.0 - sum(pesos.values()),
            4
        )

        if diferenca != 0:

            pesos[chaves[-1]] = round(
                pesos[chaves[-1]] + diferenca,
                4
            )


        # ==========================================
        # MEMÓRIA VIVA
        # ==========================================
        payload_memoria = {

            **pesos,

            "score_ultimo": round(
                media_acertos,
                4
            )
        }

        supabase.table(
            "memoria_meta_learning"
        ).insert(
            payload_memoria
        ).execute()


        # ==========================================
        # AUDITORIA HISTÓRICA
        # ==========================================
        payload_execucao = {

            "concurso_referencia": concurso_ref,

            "peso_base": pesos["peso_base"],
            "peso_global": pesos["peso_global"],
            "peso_feedback": pesos["peso_feedback"],
            "peso_regime": pesos["peso_regime"],
            "peso_moldura": pesos["peso_moldura"],
            "peso_estrutura": pesos["peso_estrutura"],
            "peso_fadiga": pesos["peso_fadiga"],
            "peso_recencia": pesos["peso_recencia"],

            "tipo_regime": tipo_regime,

            "fator_feedback": round(
                fator_feedback,
                6
            ),

            "fator_global": round(
                fator_global,
                6
            ),

            "melhor_acerto": melhor_acerto,
            "pior_acerto": pior_acerto,
            "dispersao": dispersao,

            "qtd_candidatos": qtd_palpites,

            "score_estrutural": round(
                score_estrutural,
                6
            ),

            "score_medio": round(
                media_acertos,
                6
            )
        }

        supabase.table(
            "meta_learning_execucoes"
        ).upsert(
            payload_execucao,
            on_conflict="concurso_referencia"
        ).execute()


        print(
            f"🧠 Meta-Learning Contextual | "
            f"Concurso {concurso_ref} | "
            f"Média={media_acertos:.2f} | "
            f"Best={melhor_acerto} | "
            f"Spread={dispersao}"
        )

    except Exception as e:

        print(
            f"⚠️ Erro meta-learning: {e}"
        )
