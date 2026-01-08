from fastapi import APIRouter
from app.services.estatisticas_service import (
    obter_estatisticas_com_score,
    calcular_medias_recentes,
    obter_ciclo_atual,
    obter_top_listas
)

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("")
def estatisticas():
    df = obter_estatisticas_com_score()
    medias = calcular_medias_recentes()
    ciclo = obter_ciclo_atual()
    tops = obter_top_listas(df)

    return {
        "estatisticas": df[["numero","frequencia","atraso","score"]].to_dict("records"),
        "analise": {
            **medias,
            "data_referencia": "último concurso"
        },
        "ciclo": ciclo,
        "listas": tops,
        "meta": {
            "fonte": "supabase",
            "total_numeros": 25
        }
    }
