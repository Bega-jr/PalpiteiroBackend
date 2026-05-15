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
def obter_desempenho_gerador() -> Dict[str, Any]:
    """
    Retorna o desempenho HISTÓRICO GLOBAL unificado do gerador
    usando exclusivamente a view vw_desempenho_gerador.

    ✔ Sem filtro de ano (Evita quebras de API)
    ✔ Métrica unificada do gerador como um todo
    ✔ Inclui volumetria de palpites reais
    ✔ Compatível com o formato esperado pelo front
    """

    supabase = get_supabase()

    # Adicionado 'qtd_palpites' na projeção dos campos buscados
    resp = (
        supabase
        .table("vw_desempenho_gerador")
        .select(
            """
            acertos_11,
            acertos_12,
            acertos_13,
            acertos_14,
            acertos_15,
            qtd_palpites
            """
        )
        .execute()
    )

    if not resp.data:
        return {
            "status": "ok",
            "resumo": _resumo_base(),
            "total_concursos": 0,
            "total_palpites_avaliados": 0
        }

    resumo = _resumo_base()
    total_palpites = 0

    # Soma os acertos e palpites de todas as linhas (várias versões/tipos)
    for row in resp.data:
        resumo["11"] += int(row.get("acertos_11") or 0)
        resumo["12"] += int(row.get("acertos_12") or 0)
        resumo["13"] += int(row.get("acertos_13") or 0)
        resumo["14"] += int(row.get("acertos_14") or 0)
        resumo["15"] += int(row.get("acertos_15") or 0)
        total_palpites += int(row.get("qtd_palpites") or 0)

    return {
        "status": "ok",
        "resumo": resumo,
        "total_concursos": len(resp.data),
        "total_palpites_avaliados": total_palpites
    }
