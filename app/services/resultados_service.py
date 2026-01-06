import requests
import csv
import os
from typing import List, Dict

# URL oficial que você forneceu
API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"
CSV_PATH = "app/data/Lotofacil.csv"

def fetch_concurso_api(numero: str = "") -> Dict:
    """
    Busca dados diretamente da API da Caixa.
    A Caixa exige um User-Agent para não bloquear a requisição.
    """
    try:
        url = f"{API_URL}/{numero}"
        # Headers necessários para simular um navegador e evitar erro 403/proibido
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Accept": "application/json"
        }
        # verify=False pode ser necessário se o certificado da Caixa der erro no servidor de deploy
        resp = requests.get(url, headers=headers, timeout=15, verify=True)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"Erro ao acessar API Caixa: {e}")
        return None

def load_lotofacil_data() -> List[Dict]:
    """Lê o arquivo local Lotofacil.csv"""
    if not os.path.exists(CSV_PATH):
        return []

    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            # Detecta o delimitador automaticamente (vírgula ou ponto e vírgula)
            content = f.read(1024)
            f.seek(0)
            dialect = csv.Sniffer().sniff(content) if content else None
            reader = csv.DictReader(f, dialect=dialect) if dialect else csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Erro ao ler CSV: {e}")
        return []

def normalizar_api(data: Dict) -> Dict:
    """Transforma o padrão da Caixa no padrão do seu Frontend"""
    return {
        "concurso": int(data.get("numero", 0)),
        "data": data.get("dataApuracao", ""),
        "dezenas": [int(d) for d in data.get("listaDezenas", [])]
    }
