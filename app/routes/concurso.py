from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa_completo

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def obter_ultimo_detalhado():
    """
    Endpoint: /concurso/ultimo
    Utilizado pela Home (getUltimoConcurso)
    """
    dados = buscar_na_caixa_completo("")
    if not dados:
        raise HTTPException(
            status_code=502, 
            detail="Não foi possível obter dados da API da Caixa."
        )
    return dados

@router.get("/{numero}")
def obter_por_numero(numero: str):
    """
    Endpoint: /concurso/{numero}
    Utilizado para buscas específicas
    """
    dados = buscar_na_caixa_completo(numero)
    if not dados:
        raise HTTPException(status_code=404, detail="Concurso não encontrado.")
    return dados
