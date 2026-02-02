from app.services.supabase_service import get_supabase
from typing import Dict


# ======================================================
# Base padrão
# ======================================================
def _resumo_base() -> Dict[str, int]:
    return {
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
    }


# ======================================================
# Desempenho do Gerador (FONTE ÚNICA = VIEW)
# ======================================================
def obter_desempenho_gerador(ano: int):
    """
    Retorna o desempenho NORMALIZADO do gerador
    usando exclusivamente a view vw_desempenho_gerador.

    ✔ Compatível com o front atual
    ✔ Suporta múltiplos registros no ano
    ✔ Não depende de lógica paralela
    """

    supabase = get_supabase()

    resp = (
        supabase
        .table("vw_desempenho_gerador")
        .select(
            """
            acertos_11,
            acertos_12,
            acertos_13,
            acertos_14,
            acertos_15
            """
        )
        .eq("ano", ano)
        .execute()
    )

    if not resp.data:
        return {
            "status": "ok",
            "resumo": _resumo_base(),
            "total_concursos": 0,
            "ano_referencia": ano,
        }

    resumo = _resumo_base()

    for row in resp.data:
        resumo["11"] += int(row.get("acertos_11", 0))
        resumo["12"] += int(row.get("acertos_12", 0))
        resumo["13"] += int(row.get("acertos_13", 0))
        resumo["14"] += int(row.get("acertos_14", 0))
        resumo["15"] += int(row.get("acertos_15", 0))

    return {
        "status": "ok",
        "resumo": resumo,
        "total_concursos": len(resp.data),
        "ano_referencia": ano,
    }
