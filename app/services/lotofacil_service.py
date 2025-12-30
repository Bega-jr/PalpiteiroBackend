import pandas as pd
from functools import lru_cache
import unicodedata

CSV_URL = (
    "https://raw.githubusercontent.com/"
    "Bega-jr/PalpiteiroBackend/main/data/Lotofacil.csv"
)

def _normalizar_coluna(col):
    """Remove acentos, espaços e padroniza o nome da coluna."""
    if not isinstance(col, str):
        return col
    # Remove acentos
    nfkd_form = unicodedata.normalize('NFKD', col)
    col_sem_acento = "".join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Minúsculo, remove espaços e caracteres especiais
    return col_sem_acento.strip().lower().replace(" ", "_").replace(".", "")

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

        # Agora a função existe e pode ser chamada aqui
        df.columns = [_normalizar_coluna(c) for c in df.columns]

        if "concurso" not in df.columns or df.empty:
            print("⚠️ Coluna 'concurso' não encontrada após normalização.")
            return pd.DataFrame()

        # Garante que 'concurso' seja numérico removendo possíveis erros
        df["concurso"] = pd.to_numeric(df["concurso"], errors="coerce").fillna(0).astype(int)
        
        return df

    except Exception as e:
        print("⚠️ Erro ao carregar CSV Lotofácil:", e)
        return pd.DataFrame()
