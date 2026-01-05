from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    obter_palpite_fixo_publico,
    obter_palpites_estatisticos_publico
)

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/fixo")
def palpite_fixo():
    try:
        return {
            "status": "ok",
            "tipo": "fixo",
            **obter_palpite_fixo_publico()
        }
    except Exception as e:
        print("❌ Erro palpite fixo:", e)
        raise HTTPException(status_code=500, detail="Erro ao carregar palpite fixo")


@router.get("/estatisticos")
def palpites_estatisticos():
    try:
        return {
            "status": "ok",
            "tipo": "estatisticos",
            "palpites": obter_palpites_estatisticos_publico()
        }
    except Exception as e:
        print("❌ Erro palpites estatísticos:", e)
        raise HTTPException(status_code=500, detail="Erro ao carregar palpites")
