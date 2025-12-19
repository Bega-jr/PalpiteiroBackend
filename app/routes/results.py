from fastapi import APIRouter, HTTPException
import pandas as pd

from app.services.lotofacil_service import load_lotofacil_data

router = APIRouter(prefix="/lotofacil", tags=["Lotofácil"])


@router.get("/concurso/{numero}")
def obter_concurso(numero: int):
    try:
        df = load_lotofacil_data()

        concurso = df[df["Concurso"] == numero]

        if concurso.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {numero} não encontrado"
            )

        registro = concurso.iloc[0].to_dict()

        return {
            "status": "ok",
            "concurso": registro
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar concurso {numero}: {str(e)}"
        )
