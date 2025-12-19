import pandas as pd
from fastapi import HTTPException
from app.config import DATA_FILE


def load_lotofacil_data() -> pd.DataFrame:
    try:
        df = pd.read_excel(
            DATA_FILE,
            engine="openpyxl"
        )
    except FileNotFoundError:
        raise HTTPException(
            status_code=500,
            detail="Arquivo Lotofacil.xlsx não encontrado no servidor"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao ler XLSX: {str(e)}"
        )

    df.columns = [
        "concurso",
        "data_sorteio",
        *[f"bola{i}" for i in range(1, 16)],
        "ganhadores_15",
        "cidade_uf",
        "rateio_15",
        "ganhadores_14",
        "rateio_14",
        "ganhadores_13",
        "rateio_13",
        "ganhadores_12",
        "rateio_12",
        "ganhadores_11",
        "rateio_11",
        "acumulado_15",
        "arrecadacao",
        "estimativa_premio",
        "acumulado_independencia",
        "observacao"
    ]

    return df
