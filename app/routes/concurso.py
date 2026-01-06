from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa

router = APIRouter(prefix="/concurso", tags=["Concurso"])


@router.get("/ultimo")
def obter_ultimo_da_caixa():
    """
    Retorna o último concurso da Lotofácil
    com dados 100% compatíveis com o Front.
    """
    dados = buscar_na_caixa()
    if not dados:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter os dados da Caixa no momento."
        )
    return dados


@router.get("/{numero}")
def obter_concurso_especifico(numero: str):
    """
    Retorna um concurso específico da Lotofácil.
    """
    dados = buscar_na_caixa(numero)
    if not dados:
        raise HTTPException(
            status_code=404,
            detail="Concurso não encontrado."
        )
    return dados
