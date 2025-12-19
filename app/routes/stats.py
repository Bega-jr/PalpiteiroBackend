from fastapi import APIRouter
from app.statistics import estatisticas_globais

router = APIRouter(
    prefix="/lotofacil",
    tags=["Estatísticas"]
)


@router.get("/estatisticas")
def estatisticas():
    return estatisticas_globais()

