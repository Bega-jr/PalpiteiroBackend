from fastapi import APIRouter
from app.loader import load_lotofacil_data

router = APIRouter(prefix="/lotofacil", tags=["Estatísticas"])

@router.get("/estatisticas")
def estatisticas():
    df = load_lotofacil_data()

    return {
        "total_concursos": int(df.shape[0]),
        "maior_premio": float(df["rateio_15"].max()),
        "media_arrecadacao": float(df["arrecadacao"].mean()),
        "primeiro_concurso": int(df["concurso"].min()),
        "ultimo_concurso": int(df["concurso"].max()),
    }
