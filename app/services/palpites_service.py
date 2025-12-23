import random
import datetime
from functools import lru_cache

from app.services.estatisticas_services import obter_estatisticas_base
from app.services.estatisticas_validator import filtrar_jogos_validos

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


def classificar_numeros():
    estatisticas = obter_estatisticas_base()

    return {
        "quentes": estatisticas.head(8)["numero"].tolist(),
        "equilibrados": estatisticas.iloc[8:16]["numero"].tolist(),
        "frios": estatisticas.iloc[16:22]["numero"].tolist(),
        "atrasados": estatisticas.sort_values("atraso", ascending=False)
            .head(8)["numero"].tolist()
    }


@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    g = classificar_numeros()

    jogo = (
        random.sample(g["quentes"], 6) +
        random.sample(g["equilibrados"], 5) +
        random.sample(g["frios"], 4)
    )

    jogo = sorted(set(jogo))

    if len(jogo) != 15:
        raise RuntimeError("Palpite fixo inválido")

    return jogo


def gerar_palpite_fixo():
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


def gerar_7_palpites():
    g = classificar_numeros()

    configuracoes = [
        ("Muito Quente", 8, 5, 2),
        ("Quente", 7, 6, 2),
        ("Equilibrado Quente", 5, 7, 3),
        ("Equilibrado Frio", 4, 6, 5),
        ("Frio", 3, 4, 8),
        ("Muito Frio", 2, 3, 10),
    ]

    palpites = []

    for nome, q, e, f in configuracoes:
        jogo = sorted(set(
            random.sample(g["quentes"], q) +
            random.sample(g["equilibrados"], e) +
            random.sample(g["frios"], f)
        ))

        if len(jogo) == 15:
            palpites.append(jogo)

    # Palpite 7 – fechamento atrasados + equilibrados
    jogo7 = (g["atrasados"] + g["equilibrados"])[:15]
    palpites.append(sorted(jogo7))

    return filtrar_jogos_validos(palpites)

