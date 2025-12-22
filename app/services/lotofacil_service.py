# app/services/lotofacil_service.py

import pandas as pd
from functools import lru_cache

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Bega-jr/PalpiteiroBackend/main/data/lotofacil.csv"
)


@lru_cache(maxsize=1)
def load_lotofacil_data() -> pd.DataFrame:
    """
    Carrega os dados da Lotofácil a partir de um CSV remoto.
    Usa cache em memória para evitar múltiplos downloads.
    """
    try:
        df = pd.read_csv(CSV_URL)

        if "Concurso" not in df.columns:
            raise ValueError("Coluna 'Concurso' não encontrada no CSV")

        df["Concurso"] = df["Concurso"].astype(int)

        return df

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar CSV remoto: {e}")

