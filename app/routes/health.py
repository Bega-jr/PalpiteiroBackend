from fastapi import APIRouter
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("/health/data")
def health_data():
    try:
        df = load_lotofacil_data()
        return {
            "status": "ok",
            "total_concursos": int(df.shape[0])
        }
    except Exception as e:
        return {
            "status": "erro",
            "error": str(e)
        }
