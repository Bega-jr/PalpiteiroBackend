from fastapi import APIRouter, HTTPException
from app.statistics import gerar_estatisticas_lotofacil

router = APIRouter(
    prefix="/lotofacil",
    tags=["Lotofácil - Estatísticas"]
)


@router.get("/estatisticas")
def estatisticas_lotofacil():
    try:
        return gerar_estatisticas_lotofacil()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar estatísticas da Lotofácil: {str(e)}"
        )
