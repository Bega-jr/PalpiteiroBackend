import requests
import csv
import os
from typing import List, Dict, Optional

API_URL = "servicebus2.caixa.gov.br"
CSV_PATH = "app/data/Lotofacil.csv"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=15)
        
        if resp.status_code == 200:
            d = resp.json()
            
            # --- MAPEAMENTO INTEGRAL DOS DADOS ---
            return {
                # 1. Identificação e Datas
                "concurso": d.get("numero"),
                "data": d.get("dataApuracao"),
                "proxima_data": d.get("dataProximoConcurso"),
                "local_sorteio": d.get("localSorteio"),
                "municipio_sorteio": d.get("nomeMunicipioUFSorteio"),
                
                # 2. Números Sorteados (Convertidos para Inteiros)
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "dezenas_ordem_sorteio": [int(x) for x in d.get("dezenasSorteadasOrdemSorteio", [])],
                
                # 3. Status de Acumulado
                "acumulado": d.get("acumulado", False),
                "valor_acumulado_proximo": d.get("valorAcumuladoProximoConcurso", 0.0),
                "valor_acumulado_especial": d.get("valorAcumuladoConcursoEspecial", 0.0),
                "valor_acumulado_final_05": d.get("valorAcumuladoConcurso_0_5", 0.0),
                
                # 4. Estimativas e Arrecadação
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0.0),
                "arrecadacao_total": d.get("valorArrecadado", 0.0),
                
                # 5. Rateio de Prêmios (Mapeamento da lista de objetos)
                # Faixas: 1 (15 acertos), 2 (14 acertos), 3 (13 acertos), etc.
                "rateio": [
                    {
                        "faixa": r.get("faixa"),
                        "descricao": r.get("descricaoFaixa"),
                        "ganhadores": r.get("numeroDeGanhadores"),
                        "valor_premio": r.get("valorPremio")
                    } for r in d.get("listaRateioPremio", [])
                ],
                
                # 6. Ganhadores por Região
                "listaMunicipioUFGanhadores": [
                    {
                        "posicao": m.get("posicao"),
                        "ganhadores": m.get("ganhadores"),
                        "municipio": m.get("municipio"),
                        "uf": m.get("uf")
                    } for m in d.get("listaMunicipioUFGanhadores", [])
                ],
                
                # 7. Informações Adicionais para Lógica de Navegação
                "concurso_anterior": d.get("numeroConcursoAnterior"),
                "proximo_concurso": d.get("numeroConcursoProximo"),
                "ultimo_concurso_flag": d.get("ultimoConcurso", False),
                "observacao": d.get("observacao", "")
            }
    except Exception as e:
        print(f"Erro no mapeamento: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    """Mapeia os dados do CSV para manter o mesmo contrato do buscar_na_caixa"""
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
                "acumulado": False, # CSV geralmente não possui essa info detalhada
                "rateio": [],
                "listaMunicipioUFGanhadores": []
            } for row in ultimos_raw]
    except:
        return []
