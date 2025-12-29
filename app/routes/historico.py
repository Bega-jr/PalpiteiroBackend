from fastapi import APIRouter, Depends
from app.core.auth import get_user
from app.services.historico_service import (
    salvar_jogo,
    listar_historico,
    resumo_financeiro
)

router = APIRouter(prefix="/historico", tags=["Histórico"])


@router.post("/")
def registrar(jogo: dict, user=Depends(get_user)):
    salvar_jogo(
        user_id=user.id,
        tipo=jogo["tipo"],
        numeros=jogo["numeros"],
        score=jogo.get("score")
    )
    return {"status": "ok"}


@router.get("/")
def listar(user=Depends(get_user)):
    return listar_historico(user.id)


@router.get("/resumo")
def resumo(user=Depends(get_user)):
    return resumo_financeiro(user.id)
