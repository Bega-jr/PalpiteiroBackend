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
def obter_desempenho_gerador(ano: int) -> Dict[str, Any]:
    """
    Retorna o desempenho NORMALIZADO do gerador
    usando exclusivamente a view vw_desempenho_gerador.

    ✔ Compatível com o front atual
    ✔ Suporta múltiplos registros no ano
    ✔ Não depende de lógica paralela
    """

    supabase = get_supabase()

    # Se na View a coluna 'ano' for armazenada como string/text, 
    # o PostgREST do Supabase converte tipos primitivos int/str automaticamente no .eq()
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
        # Uso do int() garante resiliência caso a View retorne os números como strings ou numeric
        resumo["11"] += int(row.get("acertos_11") or 0)
        resumo["12"] += int(row.get("acertos_12") or 0)
        resumo["13"] += int(row.get("acertos_13") or 0)
        resumo["14"] += int(row.get("acertos_14") or 0)
        resumo["15"] += int(row.get("acertos_15") or 0)

    return {
        "status": "ok",
        "resumo": resumo,
        # Mantido len() conforme sua lógica original. Se a View trouxer duplicidade de linhas 
        # por versão, este número representará o total de registros retornados da agregação.
        "total_concursos": len(resp.data),
        "ano_referencia": ano,
    }
