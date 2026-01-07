from fastapi import APIRouter
from app.services.palpites_service import obter_todos_palpites_debug

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/debug")
def debug_palpites():
    dados = obter_todos_palpites_debug()

    return {
        "status": "ok",
        "total": len(dados),
        "dados": dados
    }
