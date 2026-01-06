import requests
import csv
import os
from typing import List, Dict, Optional

API_URL = "servicebus2.caixa.gov.br"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """
    MAPEAMENTO COMPLETO: Transforma o JSON bruto da Caixa no formato 
    rico em detalhes que o seu Frontend (Home) necessita.
    """
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=15)
        
        if resp.status_code == 200:
            d = resp.json()
            
            # Extração de ganhadores da faixa 1 (15 acertos)
            rateio = d.get("listaRateioPremio", [])
            ganhadores_15 = 0
            if isinstance(rateio, list) and len(rateio) > 0:
                ganhadores_15 = rateio[0].get("numeroDeGanhadores", 0)

            # Retorno mapeado integralmente
            return {
                "concurso": d.get("numero"),
                "data": d.get("dataApuracao"),
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "acumulado": d.get("acumulado", False),
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0.0),
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0.0),
                "ganhadores_15": ganhadores_15,
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores") or [],
                # Campos extras do JSON bruto mapeados para snake_case
                "arrecadacao_total": d.get("valorArrecadado", 0.0),
                "proxima_data": d.get("dataProximoConcurso"),
                "local_sorteio": d.get("localSorteio"),
            }
    except Exception as e:
        print(f"Erro no mapeamento: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    """Mantida apenas para compatibilidade de import com a rota ultimos"""
    if not os.path.exists(CSV_PATH): return []
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = list(csv.DictReader(f))
            return reader[-quantidade:][::-1]
    except: return []
