from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    gerar_palpite_fixo,
    gerar_7_palpites
)

router = APIRouter(prefix="/palpites", tags=["Palpites"])


# =====================================================
# PALPITE FIXO (PÚBLICO)
# =====================================================

@router.get("/fixo")
def palpite_fixo():
    try:
        numeros = gerar_palpite_fixo()
        return {
            "status": "ok",
            "tipo": "palpite_fixo",
            "numeros": numeros
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar palpite fixo: {str(e)}"
        )


# =====================================================
# 7 PALPITES ESTATÍSTICOS (FUTURO VIP)
# =====================================================

@router.get("/estatisticos")
def palpites_estatisticos():
    try:
        palpites = gerar_7_palpites()
        return {
            "status": "ok",
            "tipo": "estatisticos",
            "total": len(palpites),
            "palpites": palpites
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar palpites estatísticos: {str(e)}"
        )
