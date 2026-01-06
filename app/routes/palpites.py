from fastapi import APIRouter, HTTPException
from app.services.palpites_service import (
    obter_palpite_fixo_publico,
    obter_palpites_estatisticos_publico
)

router = APIRouter(prefix="/palpites", tags=["Palpites"])


@router.get("/fixo")
def palpite_fixo():
    try:
        dados = obter_palpite_fixo_publico()
        if not dados:
            raise ValueError("Nenhum palpite fixo encontrado")

        return {
            "status": "ok",
            "tipo": "fixo",
            **dados
        }

    except Exception as e:
        print("❌ Erro palpite fixo:", e)
        raise HTTPException(
            status_code=500,
            detail="Erro ao carregar palpite fixo"
        )


@router.get("/estatisticos")
def palpites_estatisticos():
    try:
        palpites = obter_palpites_estatisticos_publico()

        return {
            "status": "ok",
            "tipo": "estatisticos",
            "palpites": palpites or []
        }

    except Exception as e:
        print("❌ Erro palpites estatísticos:", e)
        raise HTTPException(
            status_code=500,
            detail="Erro ao carregar palpites"
        )
