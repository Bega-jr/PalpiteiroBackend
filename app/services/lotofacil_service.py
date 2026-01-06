import requests
import csv
import os
from typing import List, Dict, Optional

API_URL = "servicebus2.caixa.gov.br"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """Busca dados completos na API da Caixa (inclui cidades e prêmios)"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=10)
        if resp.status_code == 200:
            d = resp.json()
            # Formata exatamente como o seu Front-end espera
            return {
                "concurso": int(d["numero"]),
                "data": d["dataApuracao"],
                "dezenas": [int(x) for x in d["listaDezenas"]],
                "acumulado": d["acumulado"],
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0),
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores", []),
                "ganhadores_15": d["listaRateioPremio"][0]["quantidadeGanhadores"] if d.get("listaRateioPremio") else 0,
                "proximo_concurso": d.get("numeroFinalConcursoProximoFinalZero", ""),
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0)
            }
    except: return None

def load_lotofacil_data() -> List[Dict]:
    """Lê o histórico do CSV"""
    if not os.path.exists(CSV_PATH): return []
    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except: return []

def get_concursos(quantidade: Optional[int] = None, numero: Optional[int] = None):
    """Função que alimenta as rotas /ultimos e /concurso"""
    if numero:
        # Se pedir um específico, tentamos a API para vir com detalhes de cidades
        res = buscar_na_caixa(str(numero))
        if res: return res
        # Se a API falhar, busca no CSV (dados básicos)
        base = load_lotofacil_data()
        return next((c for c in base if int(c["concurso"]) == numero), None)

    if quantidade == 1:
        # Se o Front pedir o último (Home), priorizamos a API para ter os detalhes da premiação
        ultimo_api = buscar_na_caixa("")
        if ultimo_api: return ultimo_api

    # Para listagens longas, usamos o CSV (mais rápido)
    base = load_lotofacil_data()
    if not base and not numero:
        return [buscar_na_caixa("")]
    
    return base[-quantidade:][::-1] if quantidade else base
