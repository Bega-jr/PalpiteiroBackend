from fastapi import APIRouter
from app.services.palpites_service import (
    obter_palpite_fixo_publico,
    obter_palpites_estatisticos_publico,
    obter_todos_palpites_publico
)

router = APIRouter(
    prefix="/palpites",
    tags=["Palpites"]
)


@router.get("/fixo")
def palpite_fixo():
    """
    Retorna o palpite fixo (indice_palpite = 0)
    """
    return obter_palpite_fixo_publico()


@router.get("/estatisticos")
def palpites_estatisticos():
    """
    Retorna todos os palpites estatísticos (indice_palpite > 0)
    """
    return obter_palpites_estatisticos_publico()


@router.get("/todos")
def todos_palpites():
    """
    Retorna fixo + estatísticos juntos (ideal para frontend)
    """
    return obter_todos_palpites_publico()
