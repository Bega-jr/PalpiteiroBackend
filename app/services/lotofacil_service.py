import pandas as pd
from app.config import localizar_arquivo_lotofacil

def load_lotofacil_data():
    path = localizar_arquivo_lotofacil()
    return str(path)
