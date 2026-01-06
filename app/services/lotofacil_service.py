import requests
import csv
import os
import urllib3
from typing import Dict, Optional, List

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "app/data/Lotofacil.csv"


def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    try:
        headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://loterias.caixa.gov.br",
            "Origin": "https://loterias.caixa.gov.br",
        }

        url = f"{API_URL}/{concurso}" if concurso else API_URL

        resp = requests.get(
            url,
            headers=headers,
            timeout=20,
            verify=False
        )

        if resp.status_code != 200:
            print("[CAIXA] status:", resp.status_code)
            return None

        try:
            d = resp.json()
        except Exception:
            print("[CAIXA] resposta não JSON")
            return None

        rateio = d.get("listaRateioPremio", [])

        def faixa(i):
            return rateio[i] if len(rateio) > i else {}

        return {
            "concurso": d.get("numero"),
            "data": d.get("dataApuracao"),
            "dezenas": [int(x) for x in d.get("listaDezenas", [])],
            "acumulado": bool(d.get("acumulado", False)),
            "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0),
            "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0),
            "proxima_data": d.get("dataProximoConcurso"),
            "arrecadacao": d.get("valorArrecadado", 0),
            "municipios": d.get("listaMunicipioUFGanhadores") or [],

            "ganhadores_15": faixa(0).get("numeroDeGanhadores", 0),
            "valor_15": faixa(0).get("valorPremio", 0),
            "ganhadores_14": faixa(1).get("numeroDeGanhadores", 0),
            "valor_14": faixa(1).get("valorPremio", 0),
            "ganhadores_13": faixa(2).get("numeroDeGanhadores", 0),
            "valor_13": faixa(2).get("valorPremio", 0),
            "ganhadores_12": faixa(3).get("numeroDeGanhadores", 0),
            "valor_12": faixa(3).get("valorPremio", 0),
            "ganhadores_11": faixa(4).get("numeroDeGanhadores", 0),
            "valor_11": faixa(4).get("valorPremio", 0),
        }

    except Exception as e:
        print("[ERRO CAIXA]", e)
        return None


def carregar_historico_csv(quantidade: int) -> List[Dict]:
    if not os.path.exists(CSV_PATH):
        return []

    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        ultimos = rows[-quantidade:][::-1]

        return [{
            "concurso": int(r.get("concurso", 0)),
            "data": r.get("data") or r.get("data_sorteio"),
            "dezenas": [int(r[f"bola{i}"]) for i in range(1, 16)],
            "municipios": [],
            "estimativa_proximo": 0,
        } for r in ultimos]

    except Exception as e:
        print("[ERRO CSV]", e)
        return []
