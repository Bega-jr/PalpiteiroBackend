from collections import defaultdict
from typing import Dict, Tuple, List
from app.services.estatisticas_service import carregar_historico, PRIMOS

# ----------------------------------
# Métricas de um jogo
# ----------------------------------
def extrair_metricas_jogo(nums: List[int]) -> Dict:
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in PRIMOS)
    soma = sum(nums)

    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]

    return {
        "pares": pares,
        "primos": primos,
        "soma": soma,
        "linhas": tuple(linhas)
    }

# ----------------------------------
# Histórico → padrões vencedores
# ----------------------------------
def calcular_score_combinacoes() -> Dict[Tuple, float]:
    historico = carregar_historico()

    padroes = defaultdict(int)
    total = len(historico)

    for h in historico:
        m = extrair_metricas_jogo(h["numeros"])

        chave = (
            round(m["soma"] / 10) * 10,   # faixa de soma
            m["pares"],
            m["primos"],
            m["linhas"]
        )

        padroes[chave] += 1

    # Normaliza score
    scores = {}
    max_freq = max(padroes.values())

    for k, v in padroes.items():
        scores[k] = round(v / max_freq, 4)

    return scores
