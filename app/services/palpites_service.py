import random
import datetime
from functools import lru_cache

from app.services.estatisticas_service import obter_estatisticas_base
# futuramente:
# from app.services.estatisticas_validator import validar_palpite


# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


# =====================================================
# FUNÇÃO AUXILIAR
# =====================================================

def _sortear(grupo, qtd):
    if not grupo:
        return []
    return random.sample(grupo, min(qtd, len(grupo)))


# =====================================================
# CLASSIFICAÇÃO DOS NÚMEROS (BASE REAL DO CSV)
# =====================================================

def classificar_numeros():
    """
    Classifica números com base em:
    - frequência (quentes / equilibrados / frios)
    - atraso real (atrasados)
    """

    df = obter_estatisticas_base()

    total = len(df)

    # 🔥 percentuais reais
    quentes = df.head(int(total * 0.30))["numero"].tolist()
    equilibrados = df.iloc[int(total * 0.30):int(total * 0.70)]["numero"].tolist()
    frios = df.tail(int(total * 0.30))["numero"].tolist()

    atrasados = (
        df.sort_values("atraso", ascending=False)
        .head(8)["numero"]
        .tolist()
    )

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }


# =====================================================
# PALPITE FIXO (CACHE DIÁRIO)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    """
    Gera um único palpite por dia (cacheado)
    """

    grupos = classificar_numeros()

    jogo = (
        _sortear(grupos["quentes"], 6) +
        _sortear(grupos["equilibrados"], 5) +
        _sortear(grupos["frios"], 4)
    )

    jogo = list(set(jogo))
    universo = list(range(1, TOTAL_NUMEROS + 1))

    while len(jogo) < NUMEROS_POR_JOGO:
        n = random.choice(universo)
        if n not in jogo:
            jogo.append(n)

    jogo = sorted(jogo)

    # futuramente:
    # if not validar_palpite(jogo):
    #     return None

    return jogo


def gerar_palpite_fixo():
    """
    Palpite fixo público – atualiza 1x por dia
    """
    hoje = datetime.date.today().isoformat()
    jogo = _palpite_fixo_cache(hoje)

    # fallback extremo (não deve acontecer)
    if not jogo:
        jogo = sorted(random.sample(range(1, 26), 15))

    return jogo


# =====================================================
# GERAÇÃO DOS 7 PALPITES ESTATÍSTICOS
# =====================================================

def gerar_7_palpites():
    grupos = classificar_numeros()

    quentes = grupos["quentes"]
    equilibrados = grupos["equilibrados"]
    frios = grupos["frios"]
    atrasados = grupos["atrasados"]

    palpites = []

    configuracoes = [
        ("Palpite 1 - Muito Quente", 8, 5, 2),
        ("Palpite 2 - Quente", 7, 6, 2),
        ("Palpite 3 - Equilibrado Quente", 5, 7, 3),
        ("Palpite 4 - Equilibrado Frio", 4, 6, 5),
        ("Palpite 5 - Frio", 3, 4, 8),
        ("Palpite 6 - Muito Frio", 2, 3, 10),
    ]

    universo = list(set(quentes + equilibrados + frios + atrasados))

    for nome, q, e, f in configuracoes:
        tentativas = 0

        while True:
            tentativas += 1

            jogo = (
                _sortear(quentes, q) +
                _sortear(equilibrados, e) +
                _sortear(frios, f)
            )

            jogo = list(set(jogo))

            while len(jogo) < NUMEROS_POR_JOGO:
                n = random.choice(universo)
                if n not in jogo:
                    jogo.append(n)

            jogo = sorted(jogo)

            # futuramente:
            # if validar_palpite(jogo):
            #     break

            break  # por enquanto aceita direto

            if tentativas > 30:
                break

        palpites.append({
            "nome": nome,
            "numeros": jogo
        })

    # =================================================
    # PALPITE 7 – ATRASADOS (PURO)
    # =================================================

    jogo7 = []

    for grupo in [atrasados, equilibrados, frios, quentes]:
        for n in grupo:
            if len(jogo7) >= NUMEROS_POR_JOGO:
                break
            if n not in jogo7:
                jogo7.append(n)

    # fallback extremo
    while len(jogo7) < NUMEROS_POR_JOGO:
        n = random.randint(1, TOTAL_NUMEROS)
        if n not in jogo7:
            jogo7.append(n)

    palpites.append({
        "nome": "Palpite 7 - Atrasados",
        "numeros": sorted(jogo7)
    })

    return palpites
