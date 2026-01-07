# app/routes/home.py
from fastapi import APIRouter, HTTPException
from app.services.home_service import obter_dados_home

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("/ultimo")
def home_ultimo():
    dados = obter_dados_home()

    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Dados do último concurso não encontrados"
        )

    return dados
