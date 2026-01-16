from app.services.supabase_service import get_supabase
from typing import Dict


def _resumo_base() -> Dict[str, int]:
    return {
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
    }


def obter_desempenho_gerador(ano: int):
    """
    Retorna desempenho NORMALIZADO do gerador
    usando EXCLUSIVAMENTE a view vw_desempenho_gerador.

    Fonte única = Supabase
    """

    supabase = get_supabase()

    resp = (
        supabase
        .table("vw_desempenho_gerador")
        .select("*")
        .eq("ano", ano)
        .single()
        .execute()
    )

    if not resp.data:
        return {
            "resumo": _resumo_base(),
            "total_concursos": 0,
            "ano_referencia": ano,
        }

    resumo = {
        "11": int(resp.data.get("11", 0)),
        "12": int(resp.data.get("12", 0)),
        "13": int(resp.data.get("13", 0)),
        "14": int(resp.data.get("14", 0)),
        "15": int(resp.data.get("15", 0)),
    }

    return {
        "resumo": resumo,
        "total_concursos": None,
        "ano_referencia": ano,
    }

