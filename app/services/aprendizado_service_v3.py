from app.services.supabase_service import get_supabase
from typing import Dict, Tuple

# --------------------------------------------------
# Limites de segurança
# --------------------------------------------------
PENALIDADE_MAX = 0.25   # até -25%
FATOR_MINIMO = 0.75     # nunca abaixo disso

# Pesos por faixa de acerto
PESO_11 = 0.03
PESO_12 = 0.10
PESO_13 = 0.30
PESO_14 = 0.60
PESO_15 = 1.00


# ==================================================
# APRIMORAMENTO GLOBAL
# ==================================================
def obter_fator_aprendizado_global(ano: int = 2026) -> Dict[str, float]:
    """
    Calcula fator global baseado em performance real do sistema.
    Versão estável (não quebra unpack e mantém compatibilidade).
    """

    supabase = get_supabase()

    res = (
        supabase
        .table("palpites_resultados_reais")
        .select("""
            qtd_palpites,
            acertos_11,
            acertos_12,
            acertos_13,
            acertos_14,
            acertos_15
        """)
        .gte("data_referencia", f"{ano}-01-01")
        .lte("data_referencia", f"{ano}-12-31")
        .execute()
    )

    # --------------------------------------------------
    # fallback seguro
    # --------------------------------------------------
    if not res.data:
        return {
            "fator": 1.0,
            "eficiencia": 0.0,
            "impacto": 0.0,
            "total_palpites": 0
        }

    impacto_total = 0.0
    total_palpites = 0

    # --------------------------------------------------
    # cálculo de impacto
    # --------------------------------------------------
    for r in res.data:
        impacto = (
            r.get("acertos_11", 0) * PESO_11 +
            r.get("acertos_12", 0) * PESO_12 +
            r.get("acertos_13", 0) * PESO_13 +
            r.get("acertos_14", 0) * PESO_14 +
            r.get("acertos_15", 0) * PESO_15
        )

        impacto_total += impacto
        total_palpites += r.get("qtd_palpites", 0)

    # --------------------------------------------------
    # eficiência real
    # --------------------------------------------------
    eficiencia = (impacto_total / total_palpites) if total_palpites > 0 else 0.0

    # --------------------------------------------------
    # fator adaptativo com limite de segurança
    # --------------------------------------------------
    penalidade = min(PENALIDADE_MAX, (1 - eficiencia) * PENALIDADE_MAX)
    fator = max(FATOR_MINIMO, 1 - penalidade)

    return {
        "fator": round(fator, 4),
        "eficiencia": round(eficiencia, 4),
        "impacto": round(impacto_total, 4),
        "total_palpites": total_palpites
    }


# ==================================================
# APLICAÇÃO DO FATOR
# ==================================================
def aplicar_fator_aprendizado(score: float, fator: float) -> float:
    """
    Aplica fator de aprendizado de forma segura
    """

    if fator <= 0:
        fator = 1.0

    return round(score * fator, 6)


# ==================================================
# UTIL EXTRA (OPCIONAL MAS MUITO ÚTIL PRO SEU GERADOR)
# ==================================================
def interpretar_fator(dados: Dict[str, float]) -> str:
    """
    Debug humano do aprendizado (opcional)
    """

    fator = dados.get("fator", 1.0)

    if fator >= 0.95:
        return "🔵 sistema estável"
    elif fator >= 0.85:
        return "🟡 leve instabilidade"
    else:
        return "🔴 alta instabilidade"
