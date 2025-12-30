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
        # Lê o CSV forçando as colunas principais como string para evitar erros de tipo
        df = pd.read_csv(
            CSV_URL,
            sep=";",
            encoding="utf-8",
            dtype=str, 
            on_bad_lines="skip"
        )

        # Normalização agressiva: remove espaços, acentos e pontos
        def limpar(c):
            return "".join(c for c in unicodedata.normalize('NFKD', c) 
                          if unicodedata.category(c) != 'Mn').lower().replace(" ", "").replace(".", "").replace("no", "")

        df.columns = [limpar(c) for c in df.columns]

        # Se não achar 'concurso', tenta a primeira coluna (que geralmente é ela)
        if "concurso" not in df.columns:
            df.rename(columns={df.columns[0]: "concurso"}, inplace=True)

        # Converte para numérico e remove linhas vazias
        df["concurso"] = pd.to_numeric(df["concurso"], errors="coerce")
        df = df.dropna(subset=["concurso"])
        
        return df
    except Exception as e:
        print(f"Erro: {e}")
        # Retorna um DataFrame com as colunas esperadas mas vazio
        return pd.DataFrame(columns=["concurso"]) 
