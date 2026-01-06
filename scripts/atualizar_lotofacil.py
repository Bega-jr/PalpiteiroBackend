import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from pandas.errors import EmptyDataError
from supabase import create_client, Client

# =========================
# CONFIG
# =========================
BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

CSV_PATH = DATA_DIR / "Lotofacil.csv"

# .strip() remove espaços ou quebras de linha acidentais
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("❌ Erro: SUPABASE_URL ou SUPABASE_KEY não foram encontrados no ambiente.")

# Garante que a URL não termine com '/' para evitar erros de rota
if SUPABASE_URL.endswith("/"):
    SUPABASE_URL = SUPABASE_URL[:-1]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABELA = "lotofacil_concursos"

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

# =========================
# FUNÇÕES SUPABASE (Com tratamento de erro)
# =========================
def ultimo_concurso_supabase():
    try:
        resp = (
            supabase.table(TABELA)
            .select("concurso")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return int(resp.data[0]["concurso"])
        return 0
    except Exception as e:
        print(f"⚠️ Erro ao consultar Supabase: {e}")
        return 0

def salvar_supabase(registros):
    if registros:
        try:
            supabase.table(TABELA).upsert(registros).execute()
        except Exception as e:
            print(f"❌ Erro ao salvar no Supabase: {e}")
            raise e

# =========================
# CSV E API (Mantidos conforme original)
# =========================
def carregar_csv():
    if not CSV_PATH.exists():
        return pd.DataFrame(columns=CAMPOS)
    try:
        df = pd.read_csv(CSV_PATH)
        return df if not df.empty else pd.DataFrame(columns=CAMPOS)
    except EmptyDataError:
        return pd.DataFrame(columns=CAMPOS)

def ultimo_concurso_csv(df):
    return int(df["concurso"].max()) if not df.empty else 0

def buscar_concurso(numero=None):
    url = BASE_URL if numero is None else f"{BASE_URL}/{numero}"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.json()

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
    dezenas = sorted(int(d) for d in dados["listaDezenas"])
    registro = {
        "loteria": "lotofacil", "concurso": int(dados["numero"]),
        "data": datetime.strptime(dados["dataApuracao"], "%d/%m/%Y").strftime("%Y-%m-%d"),
        "arrecadacao": dados["valorArrecadado"], "acumulado": dados["acumulado"],
        "estimativa_proximo": dados["valorEstimadoProximoConcurso"],
        "ganhadores_15": g15, "valor_15": v15, "ganhadores_14": g14, "valor_14": v14,
        "ganhadores_13": g13, "valor_13": v13, "ganhadores_12": g12, "valor_12": v12,
        "ganhadores_11": g11, "valor_11": v11,
    }
    for i, d in enumerate(dezenas, start=1):
        registro[f"bola{i}"] = d
    return registro

# =========================
# MAIN
# =========================
def main():
    print("🚀 Iniciando atualização...")
    df = carregar_csv()
    ultimo_csv = ultimo_concurso_csv(df)
    ultimo_db = ultimo_concurso_supabase()
    ultimo_salvo = max(ultimo_csv, ultimo_db)

    print(f"📌 Último concurso encontrado: {ultimo_salvo}")
    
    try:
        dados_api = buscar_concurso()
        ultimo_api = int(dados_api["numero"])
    except Exception as e:
        print(f"❌ Erro ao acessar API da Caixa: {e}")
        return

    novos = []
    for concurso in range(ultimo_salvo + 1, ultimo_api + 1):
        print(f"⬇️ Buscando concurso {concurso}")
        try:
            dados = buscar_concurso(concurso)
            novos.append(normalizar(dados))
        except Exception as e:
            print(f"⚠️ Pulei concurso {concurso} devido a erro: {e}")

    if not novos:
        print("✅ Nenhum concurso novo encontrado.")
        return

    # Salvar CSV
    df_novos = pd.DataFrame(novos, columns=CAMPOS)
    df_final = pd.concat([df, df_novos], ignore_index=True)
    df_final.sort_values("concurso", inplace=True)
    df_final.to_csv(CSV_PATH, index=False)
    print(f"💾 CSV atualizado: {CSV_PATH}")

    # Salvar Supabase
    salvar_supabase(novos)
    print(f"✅ Sucesso! {len(novos)} concursos adicionados.")

if __name__ == "__main__":
    main()
