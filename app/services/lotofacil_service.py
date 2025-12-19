import pandas as pd
from app.config import localizar_arquivo_lotofacil


def load_lotofacil_data() -> pd.DataFrame:
    path = localizar_arquivo_lotofacil()
    return pd.read_excel(path, engine="openpyxl")
