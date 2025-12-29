import random
import datetime
from functools import lru_cache
from app.services.historico_service import registrar_jogo
from app.services.estatisticas_service import (
    obter_estatisticas_base,
    obter_estatisticas_com_score
)
from app.services.estatisticas_validator import (
    validar_jogo,
    validar_estrutura
)

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15
QTD_FIXOS = 7

SIMILARIDADE_MAXIMA = 9
SCORE_MINIMO = 0.35


@lru_cache(maxsize=1)
def _estatisticas_com_score_cache():
    return obter_estatisticas_com_score()


def classificar_numeros():
    estatisticas = _estatisticas_com_score_cache()

    return {
        "topo": estatisticas.head(10)["numero"].tolist(),
        "meio": estatisticas.iloc[10:18]["numero"].tolist(),
        "base": estatisticas.iloc[18:25]["numero"].tolist()
    }


def gerar_fixos(grupos):
    candidatos = []

    candidatos += random.sample(grupos["topo"], min(4, len(grupos["topo"])))
    candidatos += random.sample(grupos["meio"], min(2, len(grupos["meio"])))
    candidatos += random.sample(grupos["base"], min(1, len(grupos["base"])))

    while len(set(candidatos)) < QTD_FIXOS:
        candidatos.append(random.randint(1, TOTAL_NUMEROS))

    return sorted(set(candidatos))[:QTD_FIXOS]


def similaridade(a, b):
    return len(set(a) & set(b))


def score_medio_jogo(jogo):
    df = _estatisticas_com_score_cache()
    score_map = dict(zip(df["numero"], df["score"]))
    return sum(score_map.get(n, 0) for n in jogo) / len(jogo)


@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()
    fixos = gerar_fixos(grupos)

    universo = list(set(range(1, 26)) - set(fixos))
    complemento = random.sample(universo, NUMEROS_POR_JOGO - len(fixos))

    jogo = sorted(fixos + complemento)

    estrutura = validar_estrutura(jogo)
    if estrutura["faltantes"] > 0 or estrutura["repetidos"]:
        raise RuntimeError("Erro estrutural")

    registrar_jogo(tipo="fixo", numeros=jogo)
    return jogo


def gerar_palpite_fixo():
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)
