from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter()


@router.get("/estatisticas")
def estatisticas():
    try:
        df = load_lotofacil_data()

        total_concursos = len(df)
        total_colunas = len(df.columns)

        return {
            "status": "ok",
            "total_concursos": total_concursos,
            "total_colunas": total_colunas
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao gerar estatísticas: {str(e)}"
        )
