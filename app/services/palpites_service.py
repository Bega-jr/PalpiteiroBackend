import random
import datetime
from functools import lru_cache

from app.services.historico_service import registrar_jogo
from app.services.estatisticas_service import (
    obter_estatisticas_base,
    obter_estatisticas_com_score,
    analisar_ciclo,
    obter_ultimo_resultado
)
from app.services.estatisticas_validator import (
    validar_jogo,
    validar_estrutura
)

from app.repositories.palpites_repo import (
    listar_palpites_hoje,
    carregar_palpite_fixo
)

# =====================================================
# CONFIGURAÇÕES
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15
QTD_FIXOS = 7

SIMILARIDADE_MAXIMA = 9
SCORE_MINIMO = 0.35

MODO_PADRAO = "free"

# =====================================================
# CLASSIFICAÇÃO (USADA APENAS EM GERAÇÃO OFFLINE)
# =====================================================

@lru_cache(maxsize=1)
def _estatisticas_com_score_cache():
    return obter_estatisticas_com_score()

def classificar_numeros():
    try:
        estatisticas = _estatisticas_com_score_cache()
        return {
            "topo": estatisticas.head(10)["numero"].tolist(),
            "meio": estatisticas.iloc[10:18]["numero"].tolist(),
            "base": estatisticas.iloc[18:25]["numero"].tolist()
        }
    except Exception:
        estatisticas = obter_estatisticas_base()
        return {
            "topo": estatisticas.head(8)["numero"].tolist(),
            "meio": estatisticas.iloc[8:16]["numero"].tolist(),
            "base": estatisticas.iloc[16:25]["numero"].tolist()
        }

# =====================================================
# GERAÇÃO INTELIGENTE (NÃO USADA NA API)
# =====================================================

def gerar_fixos(grupos):
    candidatos = []

    faltantes_ciclo = analisar_ciclo()
    if faltantes_ciclo:
        candidatos.extend(random.sample(faltantes_ciclo, min(2, len(faltantes_ciclo))))

    candidatos.extend(random.sample(grupos["topo"], min(3, len(grupos["topo"]))))
    candidatos.extend(random.sample(grupos["meio"], min(2, len(grupos["meio"]))))

    fixos = sorted(set(candidatos))[:QTD_FIXOS]

    while len(fixos) < QTD_FIXOS:
        n = random.randint(1, TOTAL_NUMEROS)
        if n not in fixos:
            fixos.append(n)

    return sorted(fixos)

def similaridade(a, b):
    return len(set(a) & set(b))

def jogo_diverso(jogo, existentes):
    return all(similaridade(jogo, p["numeros"]) <= SIMILARIDADE_MAXIMA for p in existentes)

@lru_cache(maxsize=1)
def _score_map_cache():
    df = _estatisticas_com_score_cache()
    return dict(zip(df["numero"], df["score"]))

def score_medio_jogo(jogo):
    score_map = _score_map_cache()
    return sum(score_map.get(n, 0) for n in jogo) / len(jogo)

# =====================================================
# API PÚBLICA (LEITURA DO SUPABASE)
# =====================================================

def obter_palpite_fixo_publico():
    numeros = carregar_palpite_fixo()
    return {"numeros": numeros}

def obter_palpites_estatisticos_publico():
    registros = listar_palpites_hoje()

    palpites = []
    for r in registros:
        palpites.append({
            "numeros": r["numeros"],
            "indice": r.get("indice_palpite")
        })

    return palpites
