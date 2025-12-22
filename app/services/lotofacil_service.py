import pandas as pd
import unicodedata
from functools import lru_cache

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Bega-jr/PalpiteiroBackend/main/data/Lotof%C3%A1cil.csv"
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
    """
    Carrega o histórico da Lotofácil a partir do CSV remoto.
    Usa cache para evitar múltiplos downloads.
    """

    try:
        df = pd.read_csv(
            CSV_URL,
            sep=";",                 # 🔥 separador correto
            encoding="utf-8",        # suporta acentos
            engine="python",         # parser tolerante
            on_bad_lines="skip"      # ignora linhas quebradas
        )

        if df.empty:
            raise RuntimeError("CSV da Lotofácil está vazio")

        # 🔹 normaliza colunas
        df.columns = [_normalizar_coluna(c) for c in df.columns]

        if "concurso" not in df.columns:
            raise RuntimeError("Coluna 'concurso' não encontrada no CSV")

        df["concurso"] = df["concurso"].astype(int)

        return df

    except Exception as e:
        raise RuntimeError(f"Erro ao carregar CSV remoto: {e}")
