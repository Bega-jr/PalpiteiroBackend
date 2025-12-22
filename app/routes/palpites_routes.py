from fastapi import APIRouter
from app.services.palpites_service import (
    gerar_7_palpites,
    gerar_palpite_fixo
)

router = APIRouter(
    prefix="/palpites",
    tags=["Palpites"]
)

# =====================================================
# PALPITE FIXO (PÚBLICO)
# =====================================================

@router.get("/fixo")
def palpite_fixo():
    jogo = gerar_palpite_fixo()
    return {
        "tipo": "palpite_fixo",
        "numeros": jogo
    }


# =====================================================
# PALPITES ESTATÍSTICOS
# =====================================================

@router.get("/estatisticos")
def palpites_estatisticos():
    palpites = gerar_7_palpites()
    return {
        "tipo": "estatisticos",
        "palpites": palpites
    }
