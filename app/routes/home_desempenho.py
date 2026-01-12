from fastapi import APIRouter, Query
from app.services.desempenho_service import obter_desempenho_gerador

router = APIRouter(prefix="/home", tags=["Home"])

@router.get("/desempenho")
def desempenho_gerador(
    ano: int = Query(2026),
    tipo_palpite: str = Query("fixo"),
    versao_gerador: str = Query("v1.0")
):
    """
    Retorna o desempenho do gerador para o ano especificado,
    considerando apenas concursos a partir do 3576 (01/01/2026)
    """

    # Chama o serviço ajustado para considerar concursos a partir do 3576
    dados = obter_desempenho_gerador(ano, tipo_palpite, versao_gerador)

    if not dados or dados["total_concursos"] == 0:
        return {
            "status": "empty",
            "ano": ano,
            "tipo_palpite": tipo_palpite,
            "versao_gerador": versao_gerador,
            "resumo": {},
            "total_concursos": 0
        }

    return {
        "status": "ok",
        "ano": ano,
        "tipo_palpite": tipo_palpite,
        "versao_gerador": versao_gerador,
        "resumo": dados["resumo"],
        "total_concursos": dados["total_concursos"],
        "info": f"Contabilizando concursos a partir do 3576 (01/01/{ano})"
    }
