from fastapi import APIRouter, HTTPException
from app.services.home_service import obter_dados_home

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("")
def home():
    try:
        dados = obter_dados_home()

        if not dados:
            raise HTTPException(
                status_code=404,
                detail="Nenhum dado encontrado para a Home"
            )

        return {
            "status": "ok",
            "data": dados
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
