from fastapi import APIRouter, HTTPException
from app.services import palpites_service
from datetime import date

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
def palpite_fixo():
    """Retorna o palpite mestre (fixo) do dia."""
    try:
        dados = palpites_service.obter_palpite_fixo_publico()
        if not dados:
            raise HTTPException(
                status_code=404,
                detail="Palpite fixo ainda não gerado para hoje."
            )
        return {
            "status": "ok",
            "tipo": "fixo",
            **dados
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        print("❌ Erro rota palpite fixo:", e)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao carregar palpite fixo"
        )

@router.get("/estatisticos")
def palpites_estatisticos():
    """Retorna a lista de palpites estatísticos validados."""
    try:
        palpites = palpites_service.obter_palpites_estatisticos_publico()
        
        return {
            "status": "ok",
            "tipo": "estatisticos",
            "data_referencia": date.today().isoformat(),
            "total": len(palpites),
            "palpites": palpites
        }
    except Exception as e:
        print("❌ Erro rota palpites estatísticos:", e)
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao carregar palpites"
        )
