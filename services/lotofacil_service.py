import pandas as pd
from app.config import LOTOFACIL_FILE


def carregar_dataframe():
    return pd.read_excel(LOTOFACIL_FILE)


def ultimos_concursos(qtd):
    df = carregar_dataframe().sort_values("Concurso", ascending=False).head(qtd)
    return df.to_dict(orient="records")


def concurso_por_numero(numero):
    df = carregar_dataframe()
    concurso = df[df["Concurso"] == numero]

    if concurso.empty:
        return {"erro": "Concurso não encontrado"}

    return concurso.iloc[0].to_dict()
