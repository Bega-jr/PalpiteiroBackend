from fastapi import APIRouter, HTTPException
from typing import List, Optional
# Importamos o serviço que consolidamos com todas as suas lógicas de CSV e Score
from app.services.estatisticas_service import (
    montar_dashboard_estatisticas,
    obter_estatisticas_com_score,
    analisar_ciclo
)
# Importamos os schemas para garantir que o FastAPI valide a saída para o React
from app.schemas.historico_schema import DashboardEstatisticas, EstatisticaNumero

router = APIRouter()

# --- NOVA ROTA PRINCIPAL (Resolve o problema da página vazia) ---
@router.get("/", response_model=DashboardEstatisticas)
def get_estatisticas_dashboard():
    """
    Esta rota retorna o objeto completo (estatisticas, analise e ciclo)
    exatamente como o seu componente React espera.
    """
    try:
        dados = montar_dashboard_estatisticas()
        return dados
    except Exception as e:
        print(f"Erro ao carregar dashboard de estatísticas: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Erro ao processar dados estatísticos para o dashboard."
        )

# --- ROTA DE SCORE (Mantém compatibilidade se você usar em outros lugares) ---
@router.get("/score", response_model=List[EstatisticaNumero])
def get_estatisticas_score_apenas():
    """
    Retorna apenas a lista de números ordenada por score.
    """
    try:
        df_score = obter_estatisticas_com_score()
        return df_score.to_dict('records')
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ROTA DE CICLO (Mantém compatibilidade caso tenha badges de ciclo em outras telas) ---
@router.get("/ciclo")
def get_numeros_ciclo():
    """
    Retorna apenas a lista de números que faltam para fechar o ciclo.
    """
    try:
        faltantes = analisar_ciclo()
        return {"faltam": sorted(faltantes), "total": len(faltantes)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
