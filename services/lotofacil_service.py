import pandas as pd


def load_lotofacil_data() -> pd.DataFrame:
    try:
        from app.config import localizar_arquivo_lotofacil

        data_file = localizar_arquivo_lotofacil()
        return pd.read_excel(data_file, engine="openpyxl")

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar dados da Lotofácil: {e}")
