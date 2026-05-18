from typing import Dict
from datetime import datetime

from app.services.supabase_service import get_supabase


# ==================================================
# DEFAULTS
# ==================================================
PESOS_DEFAULT = {
    "peso_base": 0.40,
    "peso_memoria": 0.20,
    "peso_regime": 0.15,
    "peso_feedback": 0.15,
    "peso_recencia": 0.10
}


# ==================================================
# UTIL
# ==================================================
def normalizar_pesos(
    pesos: Dict[str, float]
) -> Dict[str, float]:

    soma = sum(
        pesos.values()
    )

    if soma <= 0:

        return PESOS_DEFAULT.copy()

    return {

        k: round(
            v / soma,
            4
        )

        for k, v in pesos.items()
    }


# ==================================================
# LEITURA DOS PESOS
# ==================================================
def obter_pesos_ensemble() -> Dict[str, float]:

    supabase = get_supabase()

    try:

        rows = (

            supabase
            .table(
                "meta_learning"
            )
            .select("*")
            .order(
                "created_at",
                desc=True
            )
            .limit(1)
            .execute()
            .data
        )

        if not rows:

            return PESOS_DEFAULT.copy()

        row = rows[0]

        pesos = {

            "peso_base": float(
                row.get(
                    "peso_base",
                    PESOS_DEFAULT["peso_base"]
                )
            ),

            "peso_memoria": float(
                row.get(
                    "peso_memoria",
                    PESOS_DEFAULT["peso_memoria"]
                )
            ),

            "peso_regime": float(
                row.get(
                    "peso_regime",
                    PESOS_DEFAULT["peso_regime"]
                )
            ),

            "peso_feedback": float(
                row.get(
                    "peso_feedback",
                    PESOS_DEFAULT["peso_feedback"]
                )
            ),

            "peso_recencia": float(
                row.get(
                    "peso_recencia",
                    PESOS_DEFAULT["peso_recencia"]
                )
            )
        }

        return normalizar_pesos(
            pesos
        )

    except Exception:

        return PESOS_DEFAULT.copy()


# ==================================================
# AJUSTE AUTOMÁTICO DOS PESOS
# ==================================================
def atualizar_meta_learning(
    media_acertos: float
):

    supabase = get_supabase()

    pesos = obter_pesos_ensemble()

    try:

        # ----------------------------------------
        # PERFORMANCE BAIXA
        # ----------------------------------------
        if media_acertos < 9:

            pesos["peso_memoria"] += 0.02
            pesos["peso_feedback"] += 0.02

            pesos["peso_base"] -= 0.02
            pesos["peso_regime"] -= 0.01

        # ----------------------------------------
        # PERFORMANCE ALTA
        # ----------------------------------------
        elif media_acertos >= 11:

            pesos["peso_base"] += 0.02
            pesos["peso_regime"] += 0.01

            pesos["peso_memoria"] -= 0.01
            pesos["peso_feedback"] -= 0.01

        # ----------------------------------------
        # LIMITES DE SEGURANÇA
        # ----------------------------------------
        for k in pesos:

            pesos[k] = max(
                0.05,
                min(
                    0.60,
                    pesos[k]
                )
            )

        pesos = normalizar_pesos(
            pesos
        )

        payload = {
            **pesos,
            "created_at":
                datetime.now().isoformat()
        }

        (
            supabase
            .table(
                "meta_learning"
            )
            .insert(
                payload
            )
            .execute()
        )

        print(
            f"🧠 Meta-learning atualizado | Média={media_acertos:.2f}"
        )

    except Exception as e:

        print(
            f"⚠️ Erro meta-learning: {e}"
        )


# ==================================================
# AUDITORIA DE EXECUÇÃO
# ==================================================
def registrar_execucao_ensemble(
    concurso: int,
    pesos: Dict[str, float],
    qtd_candidatos: int,
    score_medio: float
):

    supabase = get_supabase()

    try:

        payload = {

            "concurso_referencia":
                concurso,

            "peso_base":
                pesos.get(
                    "peso_base",
                    0
                ),

            "peso_memoria":
                pesos.get(
                    "peso_memoria",
                    0
                ),

            "peso_regime":
                pesos.get(
                    "peso_regime",
                    0
                ),

            "peso_feedback":
                pesos.get(
                    "peso_feedback",
                    0
                ),

            "peso_recencia":
                pesos.get(
                    "peso_recencia",
                    0
                ),

            "qtd_candidatos":
                qtd_candidatos,

            "score_medio":
                round(
                    score_medio,
                    6
                ),

            "created_at":
                datetime.now().isoformat()
        }

        (
            supabase
            .table(
                "meta_learning_execucoes"
            )
            .upsert(
                payload,
                on_conflict="concurso_referencia"
            )
            .execute()
        )

        print(
            f"🧠 Ensemble auditado | {qtd_candidatos} candidatos"
        )

    except Exception as e:

        print(
            f"⚠️ Erro auditoria ensemble: {e}"
        )
