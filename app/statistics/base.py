import pandas as pd
from pathlib import Path

CSV_PATH = Path("app/data/Lotofacil.CSV")


def carregar_lotofacil():
    if not CSV_PATH.exists():
        raise FileNotFoundError("Arquivo Lotofacil.CSV não encontrado")

    df = pd.read_csv(CSV_PATH)

    # detecta colunas automaticamente
    colunas = [
        c for c in df.columns
        if c.lower().startswith(("bola", "dez", "n"))
    ]

    if len(colunas) != 15:
        raise ValueError("CSV deve conter exatamente 15 dezenas")

    return df[colunas]
