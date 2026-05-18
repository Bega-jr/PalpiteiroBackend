from typing import Dict
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
# LEITURA DOS PESOS
# ==================================================
def obter_pesos_ensemble() -> Dict[str, float]:

    supabase = get_supabase()

    try:

        rows = (

            supabase
            .table("meta_learning")
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
            return PESOS_DEFAULT

        row = rows[0]

        return {
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

    except Exception:

        return PESOS_DEFAULT


# ==================================================
# AJUSTE AUTOMÁTICO DOS PESOS
# ==================================================
def atualizar_meta_learning(
    media_acertos: float
):

    supabase = get_supabase()

    pesos = obter_pesos_ensemble()

    try:

        # performance ruim
        if media_acertos < 9:

            pesos["peso_memoria"] += 0.02
            pesos["peso_feedback"] += 0.02

            pesos["peso_base"] -= 0.02
            pesos["peso_regime"] -= 0.01

        # performance boa
        elif media_acertos >= 11:

            pesos["peso_base"] += 0.02
            pesos["peso_regime"] += 0.01

            pesos["peso_memoria"] -= 0.01
            pesos["peso_feedback"] -= 0.01


        # limites de segurança
        for k in pesos:

            pesos[k] = max(
                0.05,
                min(
                    0.60,
                    pesos[k]
                )
            )


        # normalização
        soma = sum(
            pesos.values()
        )

        for k in pesos:

            pesos[k] = round(
                pesos[k] / soma,
                4
            )


        supabase.table(
            "meta_learning"
        ).insert(
            pesos
        ).execute()


        print(
            f"🧠 Meta-learning atualizado | Média={media_acertos:.2f}"
        )

    except Exception as e:

        print(
            f"⚠️ Erro meta-learning: {e}"
        )
