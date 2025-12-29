import random
import datetime
from functools import lru_cache

# Mantemos o import caso queira usar em outras funções privadas, 
# mas não chamaremos nas rotas públicas.
from app.services.historico_service import registrar_jogo
from app.services.estatisticas_service import (
    obter_estatisticas_base,
    obter_estatisticas_com_score
)
from app.services.estatisticas_validator import (
    validar_jogo,
    validar_estrutura
)

# =====================================================
# CONFIGURAÇÕES
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15
QTD_FIXOS = 7

SIMILARIDADE_MAXIMA = 9
SCORE_MINIMO = 0.35

MODO_PADRAO = "free"  # free | vip

# =====================================================
# CLASSIFICAÇÃO (FREQ + ATRASO)
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
# FIXOS INTELIGENTES
# =====================================================

def gerar_fixos(grupos):
    candidatos = []
    try:
        candidatos.extend(random.sample(grupos["topo"], min(4, len(grupos["topo"]))))
        candidatos.extend(random.sample(grupos["meio"], min(2, len(grupos["meio"]))))
        candidatos.extend(random.sample(grupos["base"], min(1, len(grupos["base"]))))
    except Exception:
        pass

    while len(set(candidatos)) < QTD_FIXOS:
        candidatos.append(random.randint(1, TOTAL_NUMEROS))

    fixos = sorted(set(candidatos))[:QTD_FIXOS]
    if len(fixos) < QTD_FIXOS:
        universo = list(set(range(1, 26)) - set(fixos))
        fixos.extend(random.sample(universo, QTD_FIXOS - len(fixos)))
    return sorted(fixos)

# =====================================================
# DIVERSIDADE E SCORE
# =====================================================

def similaridade(jogo_a, jogo_b):
    return len(set(jogo_a) & set(jogo_b))

def jogo_diverso(jogo, palpites_existentes):
    for p in palpites_existentes:
        if similaridade(jogo, p["numeros"]) > SIMILARIDADE_MAXIMA:
            return False
    return True

@lru_cache(maxsize=1)
def _score_map_cache():
    df = _estatisticas_com_score_cache()
    return dict(zip(df["numero"], df["score"]))

def score_medio_jogo(jogo):
    score_map = _score_map_cache()
    return sum(score_map.get(n, 0) for n in jogo) / len(jogo)

# =====================================================
# PALPITE FIXO (VALIDADO)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()
    
    # Loop para garantir que o palpite fixo do dia seja estatisticamente bom
    for _ in range(100): 
        fixos = gerar_fixos(grupos)
        universo = list(set(range(1, 26)) - set(fixos))
        complemento = random.sample(universo, NUMEROS_POR_JOGO - len(fixos))
        jogo = sorted(fixos + complemento)

        estatistica = validar_jogo(jogo)
        if estatistica.get("aprovado"):
            return jogo
            
    # Fallback caso não ache um perfeito (não trava a rota)
    return sorted(random.sample(range(1, 26), 15))

def gerar_palpite_fixo():
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)

# =====================================================
# GERADOR DE 7 PALPITES
# =====================================================

def gerar_7_palpites(modo=MODO_PADRAO):
    grupos = classificar_numeros()
    palpites = []
    tentativas = 0

    while len(palpites) < 7 and tentativas < 150:
        tentativas += 1
        fixos = gerar_fixos(grupos)
        universo = list(set(range(1, 26)) - set(fixos))
        complemento = random.sample(universo, NUMEROS_POR_JOGO - len(fixos))
        jogo = sorted(fixos + complemento)

        estrutura = validar_estrutura(jogo)
        estatistica = validar_jogo(jogo)

        if modo == "free":
            if not estatistica.get("aprovado"):
                continue
            if estrutura["faltantes"] > 0 or estrutura["repetidos"]:
                continue

        score_medio = score_medio_jogo(jogo)
        if score_medio < SCORE_MINIMO:
            continue

        if not jogo_diverso(jogo, palpites):
            continue

        palpites.append({
            "numeros": jogo,
            "estatistica": estatistica,
            "score_medio": round(score_medio, 3)
        })

    return palpites
