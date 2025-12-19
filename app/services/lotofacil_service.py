import pandas as pd
from app.config import LOTOFACIL_FILE


def carregar_dados():
    try:
        return pd.read_excel(LOTOFACIL_FILE)
    except Exception as e:
        raise RuntimeError(f"Erro ao ler arquivo {LOTOFACIL_FILE.name}: {e}")


def ultimos_concursos(qtd):
    df = carregar_dados()
    df = df.sort_values("Concurso", ascending=False)
    return df.head(qtd).to_dict(orient="records")


def concurso_por_numero(numero):
    df = carregar_dados()
    resultado = df[df["Concurso"] == numero]
    if resultado.empty:
        return None
    return resultado.iloc[0].to_dict()


def estatisticas():
    df = carregar_dados()

    bolas = []
    for i in range(1, 16):
        bolas.extend(df[f"Bola{i}"].tolist())

    freq = pd.Series(bolas).value_counts()

    return {
        "mais_frequentes": freq.sort_values(ascending=False).head(10).to_dict(),
        "menos_frequentes": freq.sort_values().head(10).to_dict(),
        "total_concursos": int(df["Concurso"].max())
    }
