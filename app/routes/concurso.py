from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def obter_ultimo():
    dados = buscar_na_caixa("")
    if not dados:
        raise HTTPException(status_code=502, detail="Erro ao buscar dados na Caixa")
    # Retorna o dicionário mapeado, agora o React achará 'dezenas' e 'listaMunicipioUFGanhadores'
    return dados
