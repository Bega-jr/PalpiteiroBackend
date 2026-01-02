from fastapi import APIRouter, HTTPException
from app.services.lotofacil_service import load_lotofacil_data
import pandas as pd

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/{numero}")
def obter_concurso(numero: int):
    try:
        df = load_lotofacil_data()
        
        # Converte coluna para numérico para garantir a comparação
        df["concurso"] = pd.to_numeric(df["concurso"], errors="coerce")
        resultado = df[df["concurso"] == numero]

        if resultado.empty:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {numero} não encontrado"
            )

        row = resultado.iloc[0]
        
        # Monta o objeto exatamente como o componente ConcursoCard do front-end usa
        return {
            "concurso": int(row["concurso"]),
            "data": str(row["data"]),
            "dezenas": [int(row[f'bola{i}']) for i in range(1, 16) if f'bola{i}' in row]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ultimo")
def obter_ultimo_concurso():
    """Rota auxiliar para pegar o concurso mais recente"""
    try:
        df = load_lotofacil_data()
        ultimo_row = df.iloc[-1]
        
        return {
            "concurso": int(ultimo_row["concurso"]),
            "data": str(ultimo_row["data"]),
            "dezenas": [int(ultimo_row[f'bola{i}']) for i in range(1, 16)]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

