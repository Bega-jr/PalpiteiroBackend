from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def obter_ultimo():
    """Endpoint para a Home - Entrega o mapeamento completo"""
    dados = buscar_na_caixa("") # Busca o mais recente na Caixa
    if not dados:
        raise HTTPException(status_code=502, detail="Erro ao buscar dados na Caixa")
    return dados

@router.get("/{numero}")
def obter_especifico(numero: str):
    """Busca concurso específico na Caixa com mapeamento completo"""
    dados = buscar_na_caixa(numero)
    if not dados:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")
    return dados
