import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

XLSX_FILE = DATA_DIR / "lotofacil.xlsx"
CSV_FILE = DATA_DIR / "lotofacil.csv"


def load_lotofacil_data() -> pd.DataFrame:
    """
    Carrega os dados da Lotofácil.
    - Se o CSV não existir ou estiver vazio, recria a partir do XLSX
    - Se o XLSX for mais recente que o CSV, atualiza o CSV automaticamente
    """

    if not XLSX_FILE.exists():
        raise RuntimeError("Arquivo XLSX da Lotofácil não encontrado")

    # CSV não existe ou está vazio
    if not CSV_FILE.exists() or CSV_FILE.stat().st_size == 0:
        df = _criar_csv_do_xlsx()
        return df

    # XLSX atualizado depois do CSV
    if XLSX_FILE.stat().st_mtime > CSV_FILE.stat().st_mtime:
        df = _criar_csv_do_xlsx()
        return df

    # Caminho normal
    return pd.read_csv(CSV_FILE)


def _criar_csv_do_xlsx() -> pd.DataFrame:
    try:
        df = pd.read_excel(XLSX_FILE, engine="openpyxl")

        # Garantia mínima
        if "Concurso" not in df.columns:
            raise RuntimeError("Coluna 'Concurso' não encontrada no XLSX")

        df.to_csv(CSV_FILE, index=False)
        return df

    except Exception as e:
        raise RuntimeError(f"Erro ao gerar CSV a partir do XLSX: {e}")
