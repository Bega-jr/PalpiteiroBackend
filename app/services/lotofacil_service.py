import pandas as pd
from app.config import localizar_arquivo_lotofacil


def load_lotofacil_data() -> pd.DataFrame:
    try:
        arquivo = localizar_arquivo_lotofacil()

        df = pd.read_excel(
            arquivo,
            engine="openpyxl"
        )

        return df

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar dados da Lotofácil: {e}")
