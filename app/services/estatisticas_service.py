from typing import Dict, Any
from app.repositories.estatisticas_repo import carregar_estatisticas_diarias


def montar_dashboard_estatisticas() -> Dict[str, Any]:
    """
    Retorna estatísticas consolidadas JÁ PRÉ-CALCULADAS,
    prontas para consumo pelo frontend.
    NÃO executa cálculos pesados.
    """

    dados = carregar_estatisticas_diarias()

    if not dados:
        return {
            "estatisticas": [],
            "analise": None,
            "ciclo": {
                "faltam": [],
                "total_faltam": 0
            }
        }

    return {
        "estatisticas": dados.get("estatisticas", []),
        "analise": {
            "soma_media": float(dados.get("media_soma", 0)),
            "pares_media": float(dados.get("media_pares", 0)),
            "impares_media": float(
                15 - dados.get("media_pares", 0)
            ),
            "primos_media": float(dados.get("media_primos", 0)),
        },
        "ciclo": {
            "faltam": dados.get("numeros_atrasados", []),
            "total_faltam": len(dados.get("numeros_atrasados", []))
        }
    }
