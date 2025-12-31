from fastapi import APIRouter
from api.repositories.palpites_repo import listar_palpites_hoje, palpite_fixo

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/estatisticos")
def estatisticos():
    palpites = listar_palpites_hoje()
    return {
        "palpites": palpites,
        "filtros_aplicados": palpites[0]["filtros_aplicados"] if palpites else {}
    }

@router.get("/fixo")
def fixo():
    return palpite_fixo()
