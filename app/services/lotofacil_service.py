import pandas as pd
from app.config import localizar_arquivo_lotofacil


def load_lotofacil_data() -> pd.DataFrame:
    """
    Carrega o arquivo da Lotofácil independentemente de acentos no nome
    """
    path = localizar_arquivo_lotofacil()
    df = pd.read_excel(path, engine="openpyxl")
    return df
