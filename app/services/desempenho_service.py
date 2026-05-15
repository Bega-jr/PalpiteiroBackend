from app.services.supabase_service import get_supabase
from typing import Dict, Any


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
def obter_desempenho_gerador():
    """
    Retorna o desempenho HISTÓRICO GLOBAL normalizado do gerador
    usando exclusivamente a view vw_desempenho_gerador.

    ✔ Adaptado para a estrutura real da View (Sem filtro de ano)
    ✔ Compatível com o front atual
    ✔ Consolida todas as versões e tipos existentes
    """

    supabase = get_supabase()

    # Removido o filtro .eq("ano") que quebraria a execução
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
        .execute()
    )

    if not resp.data:
        return {
            "status": "ok",
            "resumo": _resumo_base(),
            "total_registros": 0
        }

    resumo = _resumo_base()

    # Soma os acertos de todas as linhas (várias versões/tipos) retornadas pela View
    for row in resp.data:
        resumo["11"] += int(row.get("acertos_11") or 0)
        resumo["12"] += int(row.get("acertos_12") or 0)
        resumo["13"] += int(row.get("acertos_13") or 0)
        resumo["14"] += int(row.get("acertos_14") or 0)
        resumo["15"] += int(row.get("acertos_15") or 0)

    return {
        "status": "ok",
        "resumo": resumo,
        "total_registros": len(resp.data)
    }

