import requests
import pandas as pd
from pathlib import Path
from datetime import datetime

# =====================================================
# CONFIGURAÇÕES
# =====================================================

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "lotofacil.csv"

COLUNAS = (
    ["concurso"] +
    [f"bola{i}" for i in range(1, 16)] +
    ["data"]
)

# =====================================================
# UTILIDADES
# =====================================================

def carregar_csv_existente() -> pd.DataFrame:
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=COLUNAS)

    df = pd.read_csv(CSV_PATH)
    return df


def ultimo_concurso_salvo(df: pd.DataFrame) -> int:
    if df.empty:
        return 0
    return int(df["concurso"].max())


def buscar_resultados_api() -> list:
    print("🌐 Consultando API da Caixa...")
    resp = requests.get(API_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data.get("listaResultado", [])


def normalizar_resultado(item: dict) -> dict:
    dezenas = [int(d) for d in item["listaDezenas"]]

    return {
        "concurso": int(item["numero"]),
        **{f"bola{i+1}": dezenas[i] for i in range(15)},
        "data": datetime.strptime(item["dataApuracao"], "%d/%m/%Y").date().isoformat()
    }


# =====================================================
# PROCESSO PRINCIPAL
# =====================================================

def atualizar_historico():
    df_existente = carregar_csv_existente()
    ultimo_salvo = ultimo_concurso_salvo(df_existente)

    print(f"📌 Último concurso salvo: {ultimo_salvo}")

    resultados_api = buscar_resultados_api()

    novos = []
    for item in resultados_api:
        numero = int(item["numero"])
        if numero > ultimo_salvo:
            novos.append(normalizar_resultado(item))

    if not novos:
        print("✅ Nenhum concurso novo para atualizar.")
        return

    df_novos = pd.DataFrame(novos, columns=COLUNAS)

    df_final = (
        pd.concat([df_existente, df_novos], ignore_index=True)
        .sort_values("concurso")
        .reset_index(drop=True)
    )

    df_final.to_csv(CSV_PATH, index=False)

    print(f"✅ {len(df_novos)} concurso(s) adicionados.")
    print(f"💾 CSV atualizado em: {CSV_PATH}")


# =====================================================
# ENTRYPOINT
# =====================================================

if __name__ == "__main__":
    try:
        atualizar_historico()
    except Exception as e:
        print(f"❌ Erro ao atualizar histórico: {e}")
        raise
