import requests
from typing import Dict, Optional

API_URL = "servicebus2.caixa.gov.br"

def buscar_na_caixa_completo(numero: str = "") -> Optional[Dict]:
    """
    Busca na API da Caixa e formata especificamente para os 
    componentes Home, ConcursoCard e as estatísticas do Front.
    """
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # Se numero for vazio, a Caixa retorna o último concurso
        resp = requests.get(f"{API_URL}/{numero}", headers=headers, timeout=15)
        
        if resp.status_code == 200:
            d = resp.json()
            
            # Extração de ganhadores da faixa principal (15 acertos)
            lista_rateio = d.get("listaRateioPremio", [])
            ganhadores_15 = 0
            if lista_rateio:
                ganhadores_15 = lista_rateio[0].get("numeroDeGanhadores", 0)

            # Mapeamento para os campos que seu Frontend (React) utiliza
            return {
                "concurso": d.get("numero"),
                "data": d.get("dataApuracao"),
                # Converte Strings da Caixa para Numbers para o cálculo de paridade do React
                "dezenas": [int(x) for x in d.get("listaDezenas", [])],
                "acumulado": d.get("acumulado", False),
                "estimativa_proximo": d.get("valorEstimadoProximoConcurso", 0.0),
                "ganhadores_15": ganhadores_15,
                # Garante que seja lista para evitar erro de .map() no Front
                "listaMunicipioUFGanhadores": d.get("listaMunicipioUFGanhadores") or [],
                # Campos extras caso o componente mude de versão
                "valor_acumulado": d.get("valorAcumuladoProximoConcurso", 0.0),
                "municipios": d.get("listaMunicipioUFGanhadores") or []
            }
    except Exception as e:
        print(f"Erro ao processar dados da Caixa: {e}")
        return None
