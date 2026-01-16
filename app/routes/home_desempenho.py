from fastapi import APIRouter, Query
from typing import Optional
from app.services.desempenho_service import obter_desempenho_gerador

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/desempenho")
def desempenho_gerador(
    ano: int = Query(2026),
    tipo_palpite: Optional[str] = Query(None),
    versao_gerador: Optional[str] = Query(None),
):
    """
    Endpoint ÚNICO e ESTÁVEL para o card de desempenho.

    - Sem filtro → soma tudo
    - Com filtro → aplica corretamente
    """

    try:
        dados = obter_desempenho_gerador(
            ano=ano,
            tipo_palpite=tipo_palpite,
            versao_gerador=versao_gerador,
        )
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
