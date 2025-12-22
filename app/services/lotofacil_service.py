import pandas as pd
import unicodedata
from functools import lru_cache

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Bega-jr/PalpiteiroBackend/main/data/lotofacil.csv"
)


def _normalizar_coluna(col: str) -> str:
    return (
        unicodedata.normalize("NFKD", col)
        .encode("ascii", "ignore")
        .decode("utf-8")
        .lower()
        .replace(" ", "_")
    )


@lru_cache(maxsize=1)
def load_lotofacil_data() -> pd.DataFrame:
    try:
        df = pd.read_csv(CSV_URL)

        if df.empty:
            raise RuntimeError("CSV da Lotofácil está vazio")

        # normaliza colunas
        df.columns = [_normalizar_coluna(c) for c in df.columns]

        if "concurso" not in df.columns:
            raise RuntimeError("Coluna 'Concurso' não encontrada no CSV")

        df["concurso"] = df["concurso"].astype(int)

        return df

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar CSV remoto: {e}")
