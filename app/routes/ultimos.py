from fastapi import APIRouter
from app.services.lotofacil_service import carregar_historico_csv

router = APIRouter(prefix="/ultimos", tags=["Histórico"])

@router.get("/{quantidade}")
def listar_ultimos(quantidade: int):
    # Se o seu front usa queryKey: ["ultimoConcurso"] e espera um ÚNICO objeto:
    res = carregar_historico_csv(quantidade)
    if quantidade == 1 and res:
        return res[0] # Retorna o objeto direto se for apenas 1
    return res
