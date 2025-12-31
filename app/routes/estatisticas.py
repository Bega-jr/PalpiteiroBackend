from fastapi import APIRouter, HTTPException
from app.repositories.estatisticas_repo import (
    carregar_estatisticas_base,
    carregar_estatisticas_score
)

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/base")
def estatisticas_base():
    try:
        return {
            "status": "ok",
            "dados": carregar_estatisticas_base()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/score")
def estatisticas_score():
    try:
        return {
            "status": "ok",
            "dados": carregar_estatisticas_score()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
