from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def obter_ultimo():
    """Rota consumida pela Home para pegar o resultado mais recente com detalhes"""
    dados = buscar_na_caixa("") # Busca o último da API
    if not dados:
        # Se a API da Caixa falhar, você pode opcionalmente buscar o último do CSV aqui
        raise HTTPException(status_code=502, detail="Serviço da Caixa indisponível")
    return dados

@router.get("/{numero}")
def obter_especifico(numero: str):
    """Busca um concurso específico por número"""
    dados = buscar_na_caixa(numero)
    if not dados:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")
    return dados

