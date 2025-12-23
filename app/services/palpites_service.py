# app/services/palpites_service.py

import random
from app.validators.estatisticas_validator import validar_jogo

TOTAL_NUMEROS = 25
TAMANHO_JOGO = 15


def gerar_jogo():
    return sorted(random.sample(range(1, TOTAL_NUMEROS + 1), TAMANHO_JOGO))


def gerar_palpites(qtd=5, tentativas_max=5000):
    palpites = []
    tentativas = 0

    while len(palpites) < qtd and tentativas < tentativas_max:
        jogo = gerar_jogo()
        resultado = validar_jogo(jogo)

        if resultado["aprovado"]:
            palpites.append({
                "jogo": jogo,
                "metricas": resultado["metricas"]
            })

        tentativas += 1

    return {
        "total_gerados": len(palpites),
        "palpites": palpites
    }
