from fastapi import APIRouter
from app.services.desempenho_service import obter_desempenho_gerador

# Mantido o prefixo /home original (A rota final acessada será /home/desempenho)
router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/desempenho")
def desempenho_gerador():
    """
    Endpoint ÚNICO, GLOBAL e ESTÁVEL para o card de desempenho.
    - Fonte: vw_desempenho_gerador (Agregada e dinâmica)
    - Sem filtro de ano para evitar quebras de contrato com o Lovable
    """
    try:
        dados = obter_desempenho_gerador()
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

    return {
        "status": "ok",
        "resumo": dados["resumo"],
        "total_concursos": dados["total_concursos"],
        "total_palpites_avaliados": dados["total_palpites_avaliados"], # Exigido pelo novo front
    }
