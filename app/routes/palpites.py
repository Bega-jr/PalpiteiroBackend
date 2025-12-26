from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    gerar_palpite_fixo,
    gerar_7_palpites
)

router = APIRouter(
    prefix="/palpites",
    tags=["Palpites"]
)

# ==========================================
# PALPITE FIXO
# ==========================================
@router.get("/fixo")
def palpite_fixo():
    try:
        numeros = gerar_palpite_fixo()
        return {
            "status": "ok",
            "tipo": "fixo",
            "numeros": numeros
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# ==========================================
# PALPITES ESTATÍSTICOS
# ==========================================
@router.get("/estatisticos")
def palpites_estatisticos():
    try:
        palpites = gerar_7_palpites()
        return {
            "status": "ok",
            "tipo": "estatistico",
            "total": len(palpites),
            "palpites": palpites
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
