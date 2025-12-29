import pandas as pd
from functools import lru_cache

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Bega-jr/PalpiteiroBackend/main/data/Lotofacil.csv"
)


@lru_cache(maxsize=1)
def load_lotofacil_data() -> pd.DataFrame:
    """
    Carrega o histórico da Lotofácil a partir do CSV remoto.
    Compatível com o CSV padronizado via API da Caixa.
    """

    try:
        df = pd.read_csv(CSV_URL)

        if df.empty:
            raise RuntimeError("CSV da Lotofácil está vazio")

        # Garantias mínimas
        if "concurso" not in df.columns:
            raise RuntimeError("Coluna 'concurso' não encontrada no CSV")

        dezenas = [f"bola{i}" for i in range(1, 16)]
        for col in dezenas:
            if col not in df.columns:
                raise RuntimeError(f"Coluna ausente no CSV: {col}")

        # Tipagem
        df["concurso"] = df["concurso"].astype(int)
        for col in dezenas:
            df[col] = df[col].astype(int)

        return df

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar CSV remoto da Lotofácil: {e}")
