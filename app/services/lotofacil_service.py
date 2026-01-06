import requests
import csv
import os
from typing import List, Dict, Optional

API_URL = "servicebus2.caixa.gov.br"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            
            # MAPEAMENTO: Transforma o padrão da Caixa no padrão do seu Front-end
            return {
                "concurso": d.get("numero"),
                "data": d.get("dataApuracao"),
                # O Front espera 'dezenas', a Caixa envia 'listaDezenas'
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "acumulado": d.get("acumulado", False),
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0),
                # Garante que lista exista para não dar erro no .forEach/map
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores") or [],
                "ganhadores_15": d["listaRateioPremio"][0]["numeroDeGanhadores"] if d.get("listaRateioPremio") else 0
            }
    except Exception as e:
        print(f"Erro ao processar API: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    if not os.path.exists(CSV_PATH):
        return []
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            ultimos_raw = reader[-quantidade:][::-1]
            return [{
                "concurso": int(row.get("concurso", 0)),
                "data": row.get("data") or row.get("data_sorteio"),
                "dezenas": [int(row[f'bola{i}']) for i in range(1, 16) if f'bola{i}' in row]
            } for row in ultimos_raw]
    except:
        return []

