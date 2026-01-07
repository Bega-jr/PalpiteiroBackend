from fastapi import APIRouter, HTTPException
from app.services import palpites_service
from datetime import date

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
def palpite_fixo():
    """Retorna o palpite mestre (fixo) do dia."""
    try:
        dados = palpites_service.obter_palpite_fixo_publico()
        
        # Se o serviço retornou None, significa que não achou o índice 0 no banco
        if not dados:
            raise HTTPException(
                status_code=404,
                detail="Palpite fixo não encontrado no banco de dados."
            )

        # Retornamos os dados diretamente, pois o service já envia:
        # {"status": "ok", "data_referencia": "...", "numeros": [...], "metricas": {...}}
        return dados

    except HTTPException as e:
        raise e
    except Exception as e:
        print(f"❌ Erro na rota /palpites/fixo: {repr(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao carregar palpite fixo"
        )

@router.get("/estatisticos")
def palpites_estatisticos():
    """Retorna a lista de palpites estatísticos validados."""
    try:
        lista_palpites = palpites_service.obter_palpites_estatisticos_publico()
        
        # Garantimos que a resposta siga o padrão esperado pelo seu Frontend
        return {
            "status": "ok",
            "tipo": "estatisticos",
            "data_referencia": date.today().isoformat(),
            "total": len(lista_palpites),
            "palpites": lista_palpites
        }
    except Exception as e:
        print(f"❌ Erro na rota /palpites/estatisticos: {repr(e)}")
        raise HTTPException(
            status_code=500,
            detail="Erro interno ao carregar palpites"
        )

