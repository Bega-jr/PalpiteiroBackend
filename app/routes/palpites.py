from fastapi import APIRouter, HTTPException
from app.services import palpites_service

router = APIRouter(prefix="/palpites", tags=["Palpites"])

@router.get("/fixo")
def palpite_fixo():
    # Retorna o dado bruto para conferir nomes de colunas e tipos
    registro = palpites_service.obter_palpite_fixo_publico()
    
    if not registro:
        raise HTTPException(status_code=404, detail="Nenhum dado encontrado")
    
    return registro

@router.get("/estatisticos")
def palpites_estatisticos():
    # Retorna a lista bruta vinda do banco
    dados = palpites_service.obter_palpites_estatisticos_publico()

    if not dados:
        return {
            "mensagem": "Banco de dados vazio ou erro na conexão",
            "dados": []
        }

    return {
        "total": len(dados),
        "dados_brutos": dados
    }
