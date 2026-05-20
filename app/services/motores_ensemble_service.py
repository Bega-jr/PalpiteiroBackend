import random
import numpy as np


# =========================================================
# MOTORES
# =========================================================
def motor_estatistico(score):

    return score


def motor_exploratorio(score):

    return score * random.uniform(
        0.92,
        1.08
    )


def motor_agressivo(score, features):

    bonus = 1.0

    if features["entropia"] > 3:
        bonus += 0.04

    if features["seq_max"] >= 4:
        bonus += 0.03

    return score * bonus


def motor_conservador(score, features):

    bonus = 1.0

    if 180 <= features["soma"] <= 210:
        bonus += 0.03

    if 6 <= features["pares"] <= 9:
        bonus += 0.03

    return score * bonus


# =========================================================
# ENSEMBLE
# =========================================================
def calcular_score_ensemble(
    score,
    features
):

    motores = [

        motor_estatistico(
            score
        ),

        motor_exploratorio(
            score
        ),

        motor_agressivo(
            score,
            features
        ),

        motor_conservador(
            score,
            features
        )
    ]

    return float(
        np.mean(motores)
    )
