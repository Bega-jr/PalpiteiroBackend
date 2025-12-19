from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_FILE = BASE_DIR / "data" / "Lotofácil.xlsx"

if not DATA_FILE.exists():
    print(f"⚠️ Arquivo XLSX não encontrado em: {DATA_FILE}")
