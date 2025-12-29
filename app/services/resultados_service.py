import requests
import csv
import os
from typing import List, Dict

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "app/data/lotofacil_resultados.csv"


# =====================================================
# API DA CAIXA
# =====================================================

def fetch_concurso_api(numero: str = "latest") -> Dict:
    try:
        url = f"{API_URL}/{numero}"
        headers = {"accept": "application/json"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


# =====================================================
# CSV (BACKUP)
# =====================================================

def load_concursos_csv() -> List[Dict]:
    if not os.path.exists(CSV_PATH):
        return []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


def get_ultimo_concurso_csv() -> Dict:
    concursos = load_concursos_csv()
    if not concursos:
        return None
    return max(concursos, key=lambda x: int(x["concurso"]))


# =====================================================
# FONTE UNIFICADA
# =====================================================

def obter_ultimo_concurso() -> Dict:
    """
    Prioridade:
    1) API Caixa
    2) CSV local (backup)
    """
    api_data = fetch_concurso_api("latest")
    if api_data:
        return normalizar_api(api_data)

    csv_data = get_ultimo_concurso_csv()
    if csv_data:
        return normalizar_csv(csv_data)

    raise RuntimeError("Nenhuma fonte de resultados disponível")


# =====================================================
# NORMALIZAÇÃO
# =====================================================

def normalizar_api(data: Dict) -> Dict:
    return {
        "concurso": data["numero"],
        "data_sorteio": data["dataApuracao"],
        "dezenas": data["listaDezenas"],
        "premio_principal": float(
            data["listaRateioPremio"][0]["valorPremio"]
        ) if data.get("listaRateioPremio") else 0.0,
        "arrecadacao": float(data.get("valorArrecadado", 0)),
        "estimativa_premio": float(data.get("valorEstimadoProximoConcurso", 0)),
        "observacao": data.get("observacao", "")
    }


def normalizar_csv(row: Dict) -> Dict:
    dezenas = [
        row[f"dezena{i}"] for i in range(1, 16)
        if f"dezena{i}" in row
    ]

    return {
        "concurso": int(row["concurso"]),
        "data_sorteio": row["data"],
        "dezenas": dezenas,
        "premio_principal": float(row.get("premio_principal", 0)),
        "arrecadacao": float(row.get("arrecadacao", 0)),
        "estimativa_premio": None,
        "observacao": ""
    }
