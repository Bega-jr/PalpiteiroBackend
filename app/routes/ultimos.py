from fastapi import APIRouter
from app.services.lotofacil_service import buscar_na_caixa, carregar_historico_csv

router = APIRouter(prefix="/ultimos", tags=["Últimos"])


@router.get("/{quantidade}")
def listar_ultimos(quantidade: int):
    if quantidade == 1:
        dados = buscar_na_caixa("")
        if dados:
            return dados

    historico = carregar_historico_csv(quantidade)

    if historico:
        return historico[0] if quantidade == 1 else historico

    return {
        "concurso": 0,
        "data": "---",
        "dezenas": [],
        "municipios": [],
        "estimativa_proximo": 0,
    }
