import pandas as pd
from functools import lru_cache

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Bega-jr/PalpiteiroBackend/main/data/Lotofacil.csv"
)


@lru_cache(maxsize=1)
def load_lotofacil_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(
            CSV_URL,
            sep=";",
            encoding="utf-8",
            engine="python",
            on_bad_lines="skip"
        )

        df.columns = [_normalizar_coluna(c) for c in df.columns]

        if "concurso" not in df.columns or df.empty:
            return pd.DataFrame()

        df["concurso"] = df["concurso"].astype(int)
        return df

    except Exception as e:
        print("⚠️ Erro ao carregar CSV Lotofácil:", e)
        return pd.DataFrame()   # 🔥 NÃO quebra o app
