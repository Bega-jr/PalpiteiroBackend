import requests
import csv
import os
import urllib3
from typing import List, Dict, Optional

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "app/data/Lotofacil.csv"


def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """
    Busca dados da Lotofácil direto da API da Caixa
    com mapeamento TOTAL alinhado ao Frontend.
    """
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
            timeout=25,
            verify=False,
        )

        if resp.status_code != 200:
            return None

        d = resp.json()
        rateio = d.get("listaRateioPremio", [])

        def faixa(idx):
            return rateio[idx] if len(rateio) > idx else {}

        return {
            # Identificação
            "concurso": d.get("numero"),
            "data": d.get("dataApuracao"),

            # Resultado
            "dezenas": [int(x) for x in d.get("listaDezenas", [])],

            # Status
            "acumulado": bool(d.get("acumulado", False)),
            "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0.0),
            "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0.0),
            "proxima_data": d.get("dataProximoConcurso"),

            # Arrecadação
            "arrecadacao": d.get("valorArrecadado", 0.0),

            # Municípios premiados
            "municipios": d.get("listaMunicipioUFGanhadores") or [],

            # Rateio completo
            "ganhadores_15": faixa(0).get("numeroDeGanhadores", 0),
            "valor_15": faixa(0).get("valorPremio", 0.0),

            "ganhadores_14": faixa(1).get("numeroDeGanhadores", 0),
            "valor_14": faixa(1).get("valorPremio", 0.0),

            "ganhadores_13": faixa(2).get("numeroDeGanhadores", 0),
            "valor_13": faixa(2).get("valorPremio", 0.0),

            "ganhadores_12": faixa(3).get("numeroDeGanhadores", 0),
            "valor_12": faixa(3).get("valorPremio", 0.0),

            "ganhadores_11": faixa(4).get("numeroDeGanhadores", 0),
            "valor_11": faixa(4).get("valorPremio", 0.0),
        }

    except Exception as e:
        print(f"[ERRO CAIXA] {e}")
        return None
