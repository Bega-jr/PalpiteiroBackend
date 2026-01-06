import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from pandas.errors import EmptyDataError
from supabase import create_client
import os

# ===============================
# CONFIG
# ===============================

BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "Lotofacil.csv"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===============================
# CAMPOS
# ===============================

CAMPOS = [
    "loteria", "concurso", "data",
    *[f"bola{i}" for i in range(1, 16)],
    "arrecadacao", "acumulado", "estimativa_proximo",
    "ganhadores_15", "valor_15",
    "ganhadores_14", "valor_14",
    "ganhadores_13", "valor_13",
    "ganhadores_12", "valor_12",
    "ganhadores_11", "valor_11",
]

# ===============================
# CSV
# ===============================

def carregar_csv():
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=CAMPOS)

    try:
        df = pd.read_csv(CSV_PATH)
        if df.empty or "concurso" not in df.columns:
            return pd.DataFrame(columns=CAMPOS)
        return df
    except EmptyDataError:
        return pd.DataFrame(columns=CAMPOS)


def ultimo_concurso_csv(df):
    if df.empty:
        return 0
    return int(df["concurso"].max())


# ===============================
# SUPABASE
# ===============================

def ultimo_concurso_supabase():
    resp = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    )

    if not resp.data:
        return 0
    return resp.data[0]["concurso"]


def salvar_supabase(registros):
    if registros:
        supabase.table("lotofacil_concursos").upsert(
            registros,
            on_conflict="concurso"
        ).execute()


# ===============================
# API CAIXA
# ===============================

def buscar_concurso(numero=None):
    url = BASE_URL if numero is None else f"{BASE_URL}/{numero}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def extrair_rateio(lista, faixa):
    for r in lista:
        if r["faixa"] == faixa:
            return r["numeroDeGanhadores"], r["valorPremio"]
    return 0, 0.0


def normalizar(dados):
    g15, v15 = extrair_rateio(dados["listaRateioPremio"], 1)
    g14, v14 = extrair_rateio(dados["listaRateioPremio"], 2)
    g13, v13 = extrair_rateio(dados["listaRateioPremio"], 3)
    g12, v12 = extrair_rateio(dados["listaRateioPremio"], 4)
    g11, v11 = extrair_rateio(dados["listaRateioPremio"], 5)

    registro = {
        "loteria": "lotofacil",
        "concurso": int(dados["numero"]),
        "data": datetime.strptime(dados["dataApuracao"], "%d/%m/%Y").strftime("%Y-%m-%d"),
        "arrecadacao": dados["valorArrecadado"],
        "acumulado": dados["acumulado"],
        "estimativa_proximo": dados["valorEstimadoProximoConcurso"],
        "ganhadores_15": g15,
        "valor_15": v15,
        "ganhadores_14": g14,
        "valor_14": v14,
        "ganhadores_13": g13,
        "valor_13": v13,
        "ganhadores_12": g12,
        "valor_12": v12,
        "ganhadores_11": g11,
        "valor_11": v11,
    }

    dezenas = sorted(int(d) for d in dados["listaDezenas"])
    for i, d in enumerate(dezenas, start=1):
        registro[f"bola{i}"] = d

    return registro


# ===============================
# MAIN
# ===============================

def main():
    df = carregar_csv()
    ultimo_csv = ultimo_concurso_csv(df)
    ultimo_db = ultimo_concurso_supabase()

    ultimo_salvo = max(ultimo_csv, ultimo_db)

    print(f"📌 Último concurso salvo: {ultimo_salvo}")

    dados_api = buscar_concurso()
    ultimo_api = int(dados_api["numero"])

    novos = []

    for concurso in range(ultimo_salvo + 1, ultimo_api + 1):
        print(f"⬇️ Buscando concurso {concurso}")
        dados = buscar_concurso(concurso)
        novos.append(normalizar(dados))

    if not novos:
        print("✅ Nenhum concurso novo.")
        return

    # CSV
    df_novos = pd.DataFrame(novos, columns=CAMPOS)
    df_final = pd.concat([df, df_novos], ignore_index=True)
    df_final.sort_values("concurso", inplace=True)
    df_final.to_csv(CSV_PATH, index=False)

    # Supabase
    salvar_supabase(novos)

    print(f"✅ {len(novos)} concursos adicionados com sucesso.")


if __name__ == "__main__":
    main()
