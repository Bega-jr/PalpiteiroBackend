import os
import requests
from datetime import datetime
from supabase import create_client, Client

# =========================
# CONFIG
# =========================
BASE_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("SUPABASE_URL ou SUPABASE_KEY não encontrados")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABELA = "lotofacil_concursos"

# =========================
# SUPABASE
# =========================
def ultimo_concurso_supabase():
    resp = (
        supabase.table(TABELA)
        .select("concurso")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    )
    return int(resp.data[0]["concurso"]) if resp.data else 0

def salvar_supabase(registros):
    resp = supabase.table(TABELA).upsert(registros).execute()
    print(f"📦 Supabase → {len(resp.data) if resp.data else 0} registros gravados")

# =========================
# API CAIXA
# =========================
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
    dezenas = sorted(int(d) for d in dados["listaDezenas"])

    g15, v15 = extrair_rateio(dados["listaRateioPremio"], 1)
    g14, v14 = extrair_rateio(dados["listaRateioPremio"], 2)
    g13, v13 = extrair_rateio(dados["listaRateioPremio"], 3)
    g12, v12 = extrair_rateio(dados["listaRateioPremio"], 4)
    g11, v11 = extrair_rateio(dados["listaRateioPremio"], 5)

    return {
        "concurso": int(dados["numero"]),
        "data": datetime.strptime(dados["dataApuracao"], "%d/%m/%Y").date(),
        "dezenas": dezenas,
        "soma": sum(dezenas),
        "pares": len([d for d in dezenas if d % 2 == 0]),
        "impares": len([d for d in dezenas if d % 2 != 0]),
        "arrecadacao": dados.get("valorArrecadado"),
        "acumulado": dados.get("acumulado"),
        "estimativa_proximo": dados.get("valorEstimadoProximoConcurso"),
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
        "municipios": dados.get("listaMunicipioUFGanhadores", []),
    }

# =========================
# MAIN
# =========================
def main():
    print("🚀 Atualizando concursos Lotofácil")

    ultimo_db = ultimo_concurso_supabase()
    print(f"📌 Último concurso no Supabase: {ultimo_db}")

    dados_api = buscar_concurso()
    ultimo_api = int(dados_api["numero"])
    print(f"🌐 Último concurso na API: {ultimo_api}")

    novos = []

    for concurso in range(ultimo_db + 1, ultimo_api + 1):
        print(f"⬇️ Buscando concurso {concurso}")
        dados = buscar_concurso(concurso)
        novos.append(normalizar(dados))

    if not novos:
        print("✅ Nenhum concurso novo.")
        return

    salvar_supabase(novos)
    print(f"✅ Finalizado: {len(novos)} concursos inseridos")

if __name__ == "__main__":
    main()
