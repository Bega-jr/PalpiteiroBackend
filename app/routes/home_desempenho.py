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
    Retorna o desempenho do gerador de palpites para o ano e tipo especificados.
    """

    try:
        # Busca os dados do desempenho
        dados = obter_desempenho_gerador(ano, tipo_palpite, versao_gerador)

        # Caso não haja registros
        if not dados:
            return {
                "status": "empty",
                "ano": ano,
                "tipo_palpite": tipo_palpite,
                "versao_gerador": versao_gerador,
                "resumo": {},
                "total_concursos": 0
            }

        # Retorno com dados agregados
        return {
            "status": "ok",
            "ano": ano,
            "tipo_palpite": tipo_palpite,
            "versao_gerador": versao_gerador,
            "resumo": {
                "11": dados["resumo"].get("11", 0),
                "12": dados["resumo"].get("12", 0),
                "13": dados["resumo"].get("13", 0),
                "14": dados["resumo"].get("14", 0),
                "15": dados["resumo"].get("15", 0),
            },
            "total_concursos": dados.get("total_concursos", 0)
        }

    except Exception as e:
        # Protege contra falhas internas
        return {
            "status": "error",
            "message": "Falha ao obter desempenho do gerador",
            "detail": str(e)
        }
