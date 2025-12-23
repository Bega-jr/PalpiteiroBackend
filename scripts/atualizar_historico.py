import requests
import pandas as pd
from pathlib import Path

# URL oficial da Caixa (Lotofácil)
URL_XLSX = "https://servicebus2.caixa.gov.br/portaldeloterias/api/resultados/download?modalidade=lotofacil"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "historico_lotofacil.csv"

def baixar_xlsx():
    print("⬇️ Baixando XLSX da Caixa...")
    response = requests.get(URL_XLSX, timeout=60)
    response.raise_for_status()
    return response.content

def converter_para_csv(xlsx_bytes):
    print("🔄 Convertendo XLSX para CSV...")
    df = pd.read_excel(xlsx_bytes)

    # Ajuste defensivo: mantém apenas colunas numéricas
    colunas_numeros = [col for col in df.columns if str(col).isdigit()]
    df = df[colunas_numeros]

    # Garante apenas 15 números por linha
    df = df.iloc[:, :15]

    df.to_csv(CSV_PATH, index=False, header=False)
    print(f"✅ CSV atualizado em: {CSV_PATH}")

def main():
    xlsx = baixar_xlsx()
    converter_para_csv(xlsx)

if __name__ == "__main__":
    main()
