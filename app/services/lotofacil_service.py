import requests
import csv
import os
from typing import List, Dict, Optional

API_URL = "servicebus2.caixa.gov.br"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """
    Busca dados detalhados da API da Caixa.
    Essencial para a HOME (estimativas, cidades, prêmios).
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        }
        # O parâmetro "" busca o último, ou um número específico
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=15)
        if resp.status_code == 200:
            d = resp.json()
            # Mapeamento exato para o que seu componente Home.tsx e ConcursoCard.tsx esperam
            return {
                "concurso": d["numero"],
                "numero": d["numero"], 
                "data": d["dataApuracao"],
                "data_concurso": d["dataApuracao"],
                "dezenas": [int(x) for x in d["listaDezenas"]],
                "acumulado": d["acumulado"],
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0),
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores", []),
                "listaRateioPremio": d.get("listaRateioPremio", []),
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0),
                "ganhadores_15": d["listaRateioPremio"][0]["quantidadeGanhadores"] if d.get("listaRateioPremio") else 0
            }
    except Exception as e:
        print(f"Erro ao acessar API Caixa: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    """
    Lê o arquivo CSV. Ideal para páginas de listagem e estatísticas.
    """
    if not os.path.exists(CSV_PATH):
        return []
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            # Pega os últimos registros do arquivo e inverte a ordem
            ultimos_raw = reader[-quantidade:][::-1]
            
            processados = []
            for row in ultimos_raw:
                # Extrai dezenas de bola1...bola15
                dezenas = [int(row[f'bola{i}']) for i in range(1, 16) if f'bola{i}' in row]
                processados.append({
                    "concurso": int(row.get("concurso", 0)),
                    "data": row.get("data") or row.get("data_sorteio"),
                    "dezenas": dezenas
                })
            return processados
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return []

