from fastapi import APIRouter, Query
from app.services.desempenho_service import obter_desempenho_gerador

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/desempenho")
def desempenho_gerador(
    ano: int = Query(2026),
):
    """
    Endpoint ÚNICO e ESTÁVEL para o card de desempenho.

    - Fonte: vw_desempenho_gerador
    - Sem soma manual
    - Sem duplicação
    """

    try:
        dados = obter_desempenho_gerador(ano=ano)
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "ano": ano,
        }

    return {
        "status": "ok",
        "ano": ano,
        "resumo": dados["resumo"],
        "total_concursos": dados["total_concursos"],
    }
