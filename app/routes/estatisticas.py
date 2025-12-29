from fastapi import APIRouter, HTTPException
from app.services.estatisticas_service import (
    obter_estatisticas_base,
    obter_estatisticas_com_score
)

router = APIRouter(
    prefix="/estatisticas",
    tags=["Estatísticas"]
)


@router.get("/base")
def estatisticas_base():
    try:
        return {
            "status": "ok",
            "dados": obter_estatisticas_base().to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/score")
def estatisticas_score():
    try:
        return {
            "status": "ok",
            "dados": obter_estatisticas_com_score().to_dict(orient="records")
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
