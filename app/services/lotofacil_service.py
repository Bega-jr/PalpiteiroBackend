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

        # Normaliza as colunas
        df.columns = [_normalizar_coluna(c) for c in df.columns]
        
        # DEBUG: Caso falhe, veremos no log da Vercel quais colunas chegaram
        print(f"DEBUG - Colunas disponíveis: {list(df.columns)}")

        # Tenta mapear nomes comuns caso 'concurso' não exista exatamente
        mapeamento = {
            'n_concurso': 'concurso',
            'numero': 'concurso',
            'no_concurso': 'concurso',
            'concurso_': 'concurso'
        }
        df = df.rename(columns=mapeamento)

        # Se mesmo assim não achar, tenta buscar qualquer coluna que CONTENHA 'concurso'
        if "concurso" not in df.columns:
            colunas_com_concurso = [c for c in df.columns if 'concurso' in c]
            if colunas_com_concurso:
                df = df.rename(columns={colunas_com_concurso[0]: 'concurso'})

        if "concurso" not in df.columns or df.empty:
            print("❌ ERRO FATAL: Coluna 'concurso' não identificada.")
            return pd.DataFrame()

        # Limpeza robusta da coluna concurso (remove pontos, espaços e converte)
        df["concurso"] = df["concurso"].astype(str).str.replace(r'\D', '', regex=True)
        df["concurso"] = pd.to_numeric(df["concurso"], errors="coerce").fillna(0).astype(int)
        
        return df

    except Exception as e:
        print("⚠️ Erro crítico ao carregar CSV:", e)
        return pd.DataFrame()

