from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    obter_palpite_fixo_publico,
    obter_palpites_estatisticos_publico
)

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/fixo")
def palpite_fixo():
    registro = obter_palpite_fixo_publico()

    if not registro:
        raise HTTPException(status_code=404, detail="Palpite fixo não encontrado")

    return {
        "status": "ok",
        **registro
    }


@router.get("/estatisticos")
def palpites_estatisticos():
    dados = obter_palpites_estatisticos_publico()

    return {
        "status": "ok",
        "data_referencia": dados["data_referencia"],
        "total": len(dados["palpites"]),
        "palpites": dados["palpites"]
    }

