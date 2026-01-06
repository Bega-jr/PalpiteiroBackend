import requests
import csv
import os
from typing import List, Dict, Optional

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """Busca na API da Caixa e mapeia para o formato do Front-end"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # URL oficial fornecida por você
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            
            # MAPEAMENTO: Transforma o bruto da Caixa no que o seu Front-end usa
            return {
                "concurso": d.get("numero"),
                "data": d.get("dataApuracao"),
                # Converte listaDezenas (strings) para dezenas (numbers)
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "acumulado": d.get("acumulado", False),
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0),
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0),
                # Garante lista vazia para evitar erro de .forEach/map no React
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores") or [],
                "ganhadores_15": d["listaRateioPremio"][0]["numeroDeGanhadores"] if d.get("listaRateioPremio") else 0
            }
    except Exception as e:
        print(f"Erro ao buscar na Caixa: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    """Lê o histórico do CSV de forma rápida"""
    if not os.path.exists(CSV_PATH):
        return []
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            ultimos_raw = reader[-quantidade:][::-1]
            return [{
                "concurso": int(row.get("concurso", 0)),
                "data": row.get("data") or row.get("data_sorteio"),
                "dezenas": [int(row[f'bola{i}']) for i in range(1, 16) if f'bola{i}' in row],
                "listaMunicipioUFGanhadores": [] # Proteção contra undefined
            } for row in ultimos_raw]
    except:
        return []
