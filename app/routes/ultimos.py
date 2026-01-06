from fastapi import APIRouter
from app.services.lotofacil_service import carregar_historico_csv

router = APIRouter(prefix="/ultimos", tags=["Histórico"])

@router.get("/{quantidade}")
def listar_ultimos(quantidade: int):
    """Rota para listagens rápidas e estatísticas usando o CSV local"""
    return carregar_historico_csv(quantidade)
))
