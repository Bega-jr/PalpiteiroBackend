import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "lotofacil.csv"

def load_lotofacil_data():
    return pd.read_csv(DATA_FILE)
