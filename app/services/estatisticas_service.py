import pandas as pd
from app.services.lotofacil_service import load_lotofacil_data


def obter_estatisticas_base():
    df = load_lotofacil_data()

    dezenas = [f"bola{i}" for i in range(1, 16)]

    frequencia = (
        df[dezenas]
        .stack()
        .value_counts()
        .sort_index()
    )

    total = frequencia.sum()

    freq_df = pd.DataFrame({
        "numero": frequencia.index.astype(int),
        "frequencia": frequencia.values
    }).sort_values("frequencia", ascending=False)

    # atraso
    ultimo_concurso = df["concurso"].max()
    atraso = {}

    for n in range(1, 26):
        ult = df[df[dezenas].isin([n]).any(axis=1)]["concurso"].max()
        atraso[n] = ultimo_concurso - ult if pd.notna(ult) else ultimo_concurso

    freq_df["atraso"] = freq_df["numero"].map(atraso)

    return freq_df.reset_index(drop=True)
