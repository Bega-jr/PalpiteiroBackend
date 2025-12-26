from fastapi import APIRouter, HTTPException
from app.models.historico_model import JogoHistorico
from app.services.historico_service import (
    salvar_jogo,
    listar_historico,
    resumo_financeiro
)

router = APIRouter(
    prefix="/historico",
    tags=["Histórico & ROI"]
)


@router.post("/registrar")
def registrar_jogo(jogo: JogoHistorico):
    try:
        salvar_jogo(jogo)
        return {"status": "ok", "mensagem": "Jogo registrado com sucesso"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
def listar():
    return {
        "status": "ok",
        "historico": listar_historico()
    }


@router.get("/resumo")
def resumo():
    return {
        "status": "ok",
        "financeiro": resumo_financeiro()
    }
