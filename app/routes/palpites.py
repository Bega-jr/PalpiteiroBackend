from fastapi import APIRouter
from app.services.palpites_service import obter_todos_palpites

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/debug")
def debug_palpites():
    """
    Endpoint de DEBUG:
    Retorna os dados crus exatamente como estão no banco.
    """
    dados = obter_todos_palpites()

    return {
        "status": "ok",
        "total": len(dados),
        "dados": dados,
    }
