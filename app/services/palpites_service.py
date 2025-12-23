import random
import datetime
from collections import Counter
from functools import lru_cache

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
# CLASSIFICAÇÃO DOS NÚMEROS
# =====================================================

def classificar_numeros(historico=None):
    """
    Classifica os números da Lotofácil em:
    quentes, equilibrados, frios e atrasados
    """

    if not historico:
        historico = []

    contador = Counter()
    for concurso in historico:
        contador.update(concurso)

    todos = list(range(1, TOTAL_NUMEROS + 1))

    frequencias = {n: contador.get(n, 0) for n in todos}

    ordenados = sorted(
        frequencias.items(),
        key=lambda x: x[1],
        reverse=True
    )

    apenas_numeros = [n for n, _ in ordenados]

    return {
        "quentes": apenas_numeros[:8],
        "equilibrados": apenas_numeros[8:16],
        "frios": apenas_numeros[16:22],
        "atrasados": apenas_numeros[22:]
    }


# =====================================================
# PALPITE FIXO (1 VEZ POR DIA)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    """
    Gera um único palpite fixo por dia
    """
    grupos = classificar_numeros()

    jogo = (
        _sortear(grupos["quentes"], 6)
        + _sortear(grupos["equilibrados"], 5)
        + _sortear(grupos["frios"], 4)
    )

    jogo = set(jogo)
    universo = list(range(1, TOTAL_NUMEROS + 1))

    while len(jogo) < NUMEROS_POR_JOGO:
        jogo.add(random.choice(universo))

    return sorted(jogo)


def gerar_palpite_fixo():
    """
    Palpite fixo público – atualiza automaticamente 1x por dia
    """
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# FECHAMENTO DOS PALPITES EQUILIBRADOS
# =====================================================

def gerar_palpites_equilibrados_fechados(qtd=3):
    """
    Gera palpites equilibrados garantindo
    cobertura total dos números (1–25)
    """
    todos = list(range(1, TOTAL_NUMEROS + 1))
    random.shuffle(todos)

    palpites = []
    indice = 0

    for i in range(qtd):
        jogo = set()

        while len(jogo) < NUMEROS_POR_JOGO:
            jogo.add(todos[indice % TOTAL_NUMEROS])
            indice += 1

        palpites.append({
            "nome": f"Palpite {i+3} - Equilibrado Fechado",
            "numeros": sorted(jogo)
        })

    return palpites


# =====================================================
# GERAÇÃO DOS 7 PALPITES (PASSO 2 + FECHAMENTO)
# =====================================================

def gerar_7_palpites(historico=None):
    grupos = classificar_numeros(historico)

    quentes = grupos["quentes"]
    equilibrados = grupos["equilibrados"]
    frios = grupos["frios"]
    atrasados = grupos["atrasados"]

    palpites = []

    # 🔥 Palpites quentes
    configuracoes_quentes = [
        ("Palpite 1 - Muito Quente", 8, 5, 2),
        ("Palpite 2 - Quente", 7, 6, 2),
    ]

    universo = list(set(quentes + equilibrados + frios + atrasados))
    if not universo:
        universo = list(range(1, TOTAL_NUMEROS + 1))

    for nome, q, e, f in configuracoes_quentes:
        jogo = (
            _sortear(quentes, q)
            + _sortear(equilibrados, e)
            + _sortear(frios, f)
        )

        jogo = set(jogo)

        while len(jogo) < NUMEROS_POR_JOGO:
            jogo.add(random.choice(universo))

        palpites.append({
            "nome": nome,
            "numeros": sorted(jogo)
        })

    # ⚖️ Palpites equilibrados com FECHAMENTO
    palpites.extend(gerar_palpites_equilibrados_fechados(3))

    # ❄️ Palpite frio
    jogo_frio = (
        _sortear(frios, 8)
        + _sortear(equilibrados, 4)
        + _sortear(quentes, 3)
    )

    jogo_frio = set(jogo_frio)

    while len(jogo_frio) < NUMEROS_POR_JOGO:
        jogo_frio.add(random.choice(universo))

    palpites.append({
        "nome": "Palpite 6 - Frio",
        "numeros": sorted(jogo_frio)
    })

    # 💤 Palpite atrasados
    jogo7 = []

    for grupo in [atrasados, equilibrados, frios, quentes]:
        for n in grupo:
            if len(jogo7) >= NUMEROS_POR_JOGO:
                break
            if n not in jogo7:
                jogo7.append(n)

    while len(jogo7) < NUMEROS_POR_JOGO:
        n = random.randint(1, TOTAL_NUMEROS)
        if n not in jogo7:
            jogo7.append(n)

    palpites.append({
        "nome": "Palpite 7 - Atrasados",
        "numeros": sorted(jogo7)
    })

    return palpites
