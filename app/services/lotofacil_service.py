import requests
from typing import Dict, Optional, List

API_URL = "https://servicebus2.caixa.gov.br/portaldeloterias/api/lotofacil"

def buscar_na_caixa(concurso: str = "") -> Optional[Dict]:
    """
    Busca os dados na API da Caixa e realiza o mapeamento completo.
    Utilizada exclusivamente para alimentar a página Home e consultas individuais.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # Se concurso for "", a API da Caixa retorna o resultado mais recente
        resp = requests.get(f"{API_URL}/{concurso}", headers=headers, timeout=15)
        
        if resp.status_code == 200:
            d = resp.json()
            
            # Extração segura dos ganhadores da faixa de 15 acertos
            rateio = d.get("listaRateioPremio", [])
            ganhadores_15 = 0
            if isinstance(rateio, list) and len(rateio) > 0:
                # O índice 0 geralmente é a faixa de 15 acertos
                ganhadores_15 = rateio[0].get("numeroDeGanhadores", 0)

            # MAPEAMENTO INTEGRAL PARA O FRONTEND
            return {
                # Identificação e Datas
                "concurso": d.get("numero"),
                "numero": d.get("numero"),
                "data": d.get("dataApuracao"),
                "data_concurso": d.get("dataApuracao"),
                "proxima_data": d.get("dataProximoConcurso"),

                # Números Sorteados (Convertidos para Números para o React)
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "dezenas_ordem_sorteio": [int(x) for x in d.get("dezenasSorteadasOrdemSorteio", [])],

                # Status de Acumulado e Prêmios
                "acumulado": d.get("acumulado", False),
                "ganhadores_15": ganhadores_15,
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0.0),
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0.0),
                "arrecadacao_total": d.get("valorArrecadado", 0.0),

                # Localização (Cidades) - Garante lista vazia se for null
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores") or [],
                "municipios": d.get("listaMunicipioUFGanhadores") or [],

                # Local do Sorteio
                "local_sorteio": d.get("localSorteio"),
                "municipio_sorteio": d.get("nomeMunicipioUFSorteio")
            }
    except Exception as e:
        print(f"Erro ao buscar/mapear dados da Caixa: {e}")
        return None

def carregar_historico_csv(quantidade: int) -> List[Dict]:
    """
    Mantida apenas com retorno vazio para não quebrar o import da rota 'ultimos'.
    Foco total na API da Caixa.
    """
    return []
