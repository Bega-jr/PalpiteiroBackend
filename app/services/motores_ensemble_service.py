import random
import numpy as np


# =========================================================
# HELPERS
# =========================================================
def limitar(
    valor,
    minimo=0.0,
    maximo=1.5
):

    return max(
        minimo,
        min(valor, maximo)
    )


# =========================================================
# MOTORES
# =========================================================
def motor_estatistico(
    score_estatistico
):

    return score_estatistico


def motor_montecarlo(
    score_montecarlo
):

    return score_montecarlo


def motor_global(
    fator_global
):

    return fator_global


def motor_feedback(
    fator_feedback
):

    return fator_feedback


def motor_regime(
    fator_regime
):

    return fator_regime


# =========================================================
# ENSEMBLE CENTRAL
# =========================================================
def calcular_score_ensemble(

    score_estatistico,

    score_montecarlo,

    fator_global,

    fator_feedback,

    fator_regime,

    bonus_estrutura=1.0,

    bonus_fadiga=1.0,

    bonus_recencia=1.0,

    bonus_moldura=1.0,

    bonus_recompensa=1.0,

    pesos=None,

    **kwargs
):

    # =====================================================
    # PESOS DEFAULT
    # =====================================================
    if pesos is None:

        pesos = {

            "peso_base": 0.40,

            "peso_global": 0.15,

            "peso_feedback": 0.10,

            "peso_regime": 0.10,

            "peso_moldura": 0.08,

            "peso_estrutura": 0.07,

            "peso_fadiga": 0.05,

            "peso_recompensa": 0.08

            "peso_recencia": 0.05
        }

    # =====================================================
    # NORMALIZA
    # =====================================================
    score_estatistico = limitar(
        score_estatistico
    )

    score_montecarlo = limitar(
        score_montecarlo
    )

    fator_global = limitar(
        fator_global
    )

    fator_feedback = limitar(
        fator_feedback
    )

    fator_regime = limitar(
        fator_regime
    )

    bonus_estrutura = limitar(
        bonus_estrutura
    )

    bonus_fadiga = limitar(
        bonus_fadiga
    )

    bonus_recencia = limitar(
        bonus_recencia
    )

    bonus_moldura = limitar(
        bonus_moldura
    )

    bonus_recompensa = limitar(
        bonus_recompensa
    )

    # =====================================================
    # BASE
    # =====================================================
    score = (

        score_estatistico
        * pesos["peso_base"]

        +

        score_montecarlo
        * 0.15
    )

    # =====================================================
    # FATORES
    # =====================================================
    score *= (

        1

        +

        (
            (fator_global - 1)
            * pesos["peso_global"]
        )

        +

        (
            (fator_feedback - 1)
            * pesos["peso_feedback"]
        )

        +

        (
            (fator_regime - 1)
            * pesos["peso_regime"]
        )
    )

    # =====================================================
    # BÔNUS
    # =====================================================
    score *= (

        bonus_moldura
        ** pesos["peso_moldura"]

    )

    score *= (

        bonus_estrutura
        ** pesos["peso_estrutura"]

    )

    score *= (

        bonus_fadiga
        ** pesos["peso_fadiga"]

    )

    score *= (

        bonus_recencia
        ** pesos["peso_recencia"]

    )

    score *= (

        bonus_recompensa
        ** pesos["peso_recompensa"]
    
    )

    # =====================================================
    # ENTROPIA CONTROLADA
    # =====================================================
    score *= random.uniform(
        0.995,
        1.005
    )

    return round(
        float(score),
        8
    )
