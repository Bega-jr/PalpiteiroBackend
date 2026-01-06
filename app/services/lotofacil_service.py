import requests
import csv
import os
import urllib3
from typing import List, Dict, Optional

# Desativa avisos de SSL (importante para evitar lentidão em servidores governamentais)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

API_URL = "servicebus2.caixa.gov.br"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """
    Busca dados na API da Caixa com tratamento para evitar erro 502/Timeout.
    Mapeia integralmente para o formato do Frontend.
    """
    try:
        # Headers robustos para evitar bloqueio de DataCenter (Vercel)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "loterias.caixa.gov.br",
            "Origin": "https://loterias.caixa.gov.br"
        }
        
        # Aumentamos o timeout para 25 segundos (limite da Vercel) e verify=False
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=25, verify=False)
        
        if resp.status_code == 200:
            d = resp.json()
            
            # Extração de ganhadores da faixa 1 (15 acertos)
            rateio = d.get("listaRateioPremio", [])
            ganhadores_15 = 0
            if isinstance(rateio, list) and len(rateio) > 0:
                # O índice 0 é a faixa principal de 15 acertos
                ganhadores_15 = rateio[0].get("numeroDeGanhadores", 0)

            # MAPEAMENTO COMPLETO
            return {
                "concurso": d.get("numero"),
                "numero": d.get("numero"),
                "data": d.get("dataApuracao"),
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "acumulado": d.get("acumulado", False),
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0.0),
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0.0),
                "ganhadores_15": ganhadores_15,
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores") or [],
                "municipios": d.get("listaMunicipioUFGanhadores") or [],
                "arrecadacao_total": d.get("valorArrecadado", 0.0),
                "proxima_data": d.get("dataProximoConcurso")
            }
        return None
    except Exception as e:
        print(f"Erro na conexão/mapeamento da Caixa: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    """Retorno básico do histórico via CSV"""
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
                "listaMunicipioUFGanhadores": []
            } for row in ultimos_raw]
    except:
        return []
