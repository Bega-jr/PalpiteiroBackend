from fastapi import APIRouter
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("/health")
def health():
    try:
        df = load_lotofacil_data()

        return {
            "status": "healthy",
            "fonte": "csv_remoto",
            "total_concursos": int(df.shape[0]),
            "ultima_coluna": df.columns[-1]
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
