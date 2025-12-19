import pandas as pd
from app.config import localizar_arquivo_lotofacil


def load_lotofacil_data() -> pd.DataFrame:
    """
    Carrega o arquivo oficial da Lotofácil (XLSX)
    e retorna um DataFrame pandas.
    """
    arquivo = localizar_arquivo_lotofacil()
    df = pd.read_excel(arquivo, engine="openpyxl")
    return df
