from fastapi import APIRouter
from app.statistics import estatisticas_globais

router = APIRouter(
    prefix="/lotofacil",
    tags=["Estatísticas"]
)


@router.get(
    "/estatisticas",
    summary="Estatísticas completas da Lotofácil",
    description="""
Retorna estatísticas completas da Lotofácil brasileira, calculadas
diretamente a partir do arquivo XLSX oficial da Caixa.

Inclui:
- Total de concursos
- Intervalo de concursos
- Frequência de dezenas (01 a 25)
- Dezenas mais e menos sorteadas
- Pares x ímpares
- Soma das dezenas
- Estatísticas de prêmios
- Estatísticas de arrecadação
- Análise de sequências consecutivas
"""
)
def estatisticas():
    """
    Endpoint principal de estatísticas globais da Lotofácil.
    """
    return estatisticas_globais()
