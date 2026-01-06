from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def obter_ultimo_da_caixa():
    """Endpoint chamado pela Home para obter o último resultado mapeado"""
    dados = buscar_na_caixa("") # Busca o mais recente via API
    if not dados:
        raise HTTPException(
            status_code=502, 
            detail="Não foi possível obter os dados da Caixa no momento."
        )
    return dados

@router.get("/{numero}")
def obter_especifico_da_caixa(numero: str):
    """Busca um concurso específico via API"""
    dados = buscar_na_caixa(numero)
    if not dados:
        raise HTTPException(status_code=404, detail="Concurso não encontrado.")
    return dados
