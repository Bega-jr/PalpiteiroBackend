from fastapi import APIRouter
from app.services.lotofacil_service import buscar_na_caixa, carregar_historico_csv

router = APIRouter(prefix="/ultimos", tags=["Loterias"])

@router.get("/{quantidade}")
def listar_ultimos(quantidade: int):
    # Se for a Home pedindo o último (quantidade = 1)
    if quantidade == 1:
        dados = buscar_na_caixa("") # Pega direto da API da Caixa mapeado
        if dados:
            return dados # Se seu Front usa getUltimoConcurso (objeto unico)
            # Se o front esperar um array, use: return [dados]
            
    # Para histórico, usa o CSV
    return carregar_historico_csv(quantidade)
