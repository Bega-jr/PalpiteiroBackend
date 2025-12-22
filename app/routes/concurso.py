from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data
import pandas as pd

router = APIRouter()


# ✅ ROTA FIXA PRIMEIRO
@router.get("/concurso/ultimo")
def obter_ultimo_concurso():
    try:
        df = load_lotofacil_data()

        if "concurso" not in df.columns:
            raise HTTPException(
                status_code=500,
                detail="Coluna 'concurso' não encontrada"
            )

        df["concurso"] = pd.to_numeric(df["concurso"], errors="coerce")

        ultimo = df.sort_values("concurso").iloc[-1]
        ultimo = ultimo.where(pd.notnull(ultimo), None)

        return {
            "status": "ok",
            "concurso": ultimo.to_dict()
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao buscar último concurso: {str(e)}"
        )


# ✅ ROTA DINÂMICA DEPOIS
@router.get("/concurso/{numero}")
def obter_concurso(numero: int):
    try:
        df = load_lotofacil_data()

        if "concurso" not in df.columns:
            raise HTTPException(
                status_code=500,
                detail=f"Coluna 'concurso' não encontrada. Colunas: {list(df.columns)}"
            )

        df["concurso"] = pd.to_numeric(df["concurso"], errors="coerce")

        resultado = df[df["concurso"] == numero]

        if resultado.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {numero} não encontrado"
            )

        registro = resultado.iloc[0].where(pd.notnull(resultado.iloc[0]), None)

        return {
            "status": "ok",
            "concurso": registro.to_dict()
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno concurso: {str(e)}"
        )

