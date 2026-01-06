from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import buscar_na_caixa

router = APIRouter(prefix="/concurso", tags=["Concurso"])


@router.get("/ultimo")
def ultimo_concurso():
    dados = buscar_na_caixa("")
    if not dados:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível obter dados da Caixa"
        )
    return dados


@router.get("/{numero}")
def concurso_por_numero(numero: str):
    dados = buscar_na_caixa(numero)
    if not dados:
        raise HTTPException(status_code=404, detail="Concurso não encontrado")
    return dados
