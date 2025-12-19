import pandas as pd
from pathlib import Path
from datetime import datetime

# 📁 caminhos seguros (funciona local + Vercel)
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

EXCEL_FILE = DATA_DIR / "lotofacil.xlsx"
CSV_FILE = DATA_DIR / "lotofacil.csv"


def _excel_existe() -> bool:
    return EXCEL_FILE.exists()


def _csv_existe() -> bool:
    return CSV_FILE.exists()


def _csv_esta_desatualizado() -> bool:
    if not _csv_existe() or not _excel_existe():
        return True

    return EXCEL_FILE.stat().st_mtime > CSV_FILE.stat().st_mtime


def _gerar_csv_do_excel():
    df = pd.read_excel(EXCEL_FILE)
    df.to_csv(CSV_FILE, index=False)


def load_lotofacil_data() -> pd.DataFrame:
    """
    Carrega os dados da Lotofácil de forma segura:
    - Usa CSV (performance)
    - Atualiza automaticamente se o Excel mudar
    """

    if _excel_existe() and _csv_esta_desatualizado():
        _gerar_csv_do_excel()

    if not _csv_existe():
        raise RuntimeError("Arquivo CSV da Lotofácil não encontrado")

    df = pd.read_csv(CSV_FILE)

    # 🔥 normalização crítica
    if "Concurso" in df.columns:
        df["Concurso"] = df["Concurso"].astype(int)

    return df
