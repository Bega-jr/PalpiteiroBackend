import random
import numpy as np

# =========================================================
# HELPERS
# =========================================================
def limitar(valor, minimo, maximo):
    """Garante que o valor fique estritamente dentro do intervalo definido."""
    return max(minimo, min(valor, maximo))

# =========================================================
# ENSEMBLE CENTRAL
# =========================================================
def calcular_score_ensemble(
    score_estatistico,
    score_montecarlo,
    score_potencial=0.0,
    fator_global=1.0,
    fator_feedback=1.0,
    fator_regime=1.0,
    bonus_estrutura=1.0,
    bonus_fadiga=1.0,
    bonus_recencia=1.0,
    bonus_moldura=1.0,
    bonus_recompensa=1.0,
    pesos=None,
    **kwargs
):
    # Dicionário interno de fallbacks caso falte alguma chave individual
    valores_padrao = {
        "peso_base": 0.35,
        "peso_montecarlo": 0.15,
        "peso_potencial": 0.25,
        "peso_global": 0.10,
        "peso_feedback": 0.08,
        "peso_regime": 0.07,
        "peso_moldura": 0.06,
        "peso_estrutura": 0.05,
        "peso_fadiga": 0.04,
        "peso_recencia": 0.04,
        "peso_recompensa": 0.06
    }

    if pesos is None:
        pesos = valores_padrao

    # Normalização explícita com os limites corretos
    score_estatistico = limitar(score_estatistico, 0.0, 1.6)
    score_montecarlo = limitar(score_montecarlo, 0.0, 1.6)
    score_potencial = limitar(score_potencial, 0.0, 2.0)

    # Cálculo do Score Base Ponderado usando fallbacks seguros
    score = (
        score_estatistico * pesos.get("peso_base", valores_padrao["peso_base"]) +
        score_montecarlo * pesos.get("peso_montecarlo", valores_padrao["peso_montecarlo"]) +
        score_potencial * pesos.get("peso_potencial", valores_padrao["peso_potencial"])
    )

    # Aplicação dos fatores multiplicativos
    score *= (
        1 +
        (fator_global - 1) * pesos.get("peso_global", valores_padrao["peso_global"]) +
        (fator_feedback - 1) * pesos.get("peso_feedback", valores_padrao["peso_feedback"]) +
        (fator_regime - 1) * pesos.get("peso_regime", valores_padrao["peso_regime"])
    )

    # Aplicação sequencial dos bônus
    bonus_chaves = ["moldura", "estrutura", "fadiga", "recencia", "recompensa"]
    locais = locals()
    
    for chave in bonus_chaves:
        valor_bonus = locais[f"bonus_{chave}"]
        peso_chave = f"peso_{chave}"
        # Aplica o .get() com o fallback correto mapeado do dicionário padrão
        score *= (1 + (valor_bonus - 1) * pesos.get(peso_chave, valores_padrao[peso_chave]))

    # Injeção de entropia controlada leve
    score *= random.uniform(0.993, 1.007)

    return round(float(score), 8)
