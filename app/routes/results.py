from fastapi import APIRouter
from app.services import get_concurso, get_ultimos_concursos

router = APIRouter(
    prefix="/lotofacil",
    tags=["Resultados"]
)


@router.get("/concurso/{concurso_id}")
def concurso(concurso_id: int):
    return get_concurso(concurso_id)


@router.get("/ultimos/{quantidade}")
def ultimos(quantidade: int):
    return {
        "quantidade": quantidade,
        "concursos": get_ultimos_concursos(quantidade)
    }
