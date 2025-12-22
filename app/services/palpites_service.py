import random
from collections import Counter

# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


# =====================================================
# FUNÇÃO AUXILIAR
# =====================================================

def _sortear(grupo, qtd):
    return random.sample(grupo, min(qtd, len(grupo)))


# =====================================================
# CLASSIFICAÇÃO DOS NÚMEROS
# =====================================================

def classificar_numeros(historico=None):
    """
    Classifica os números da Lotofácil em:
    quentes, equilibrados, frios e atrasados
    """

    # 🔹 fallback caso ainda não venha histórico da API
    if not historico:
        historico = []

    # Conta frequência
    contador = Counter()
    for concurso in historico:
        contador.update(concurso)

    todos = list(range(1, TOTAL_NUMEROS + 1))

    # Frequência padrão caso histórico esteja vazio
    frequencias = {n: contador.get(n, 0) for n in todos}

    # Ordena por frequência
    ordenados = sorted(frequencias.items(), key=lambda x: x[1], reverse=True)
    apenas_numeros = [n for n, _ in ordenados]

    quentes = apenas_numeros[:8]
    equilibrados = apenas_numeros[8:16]
    frios = apenas_numeros[16:22]
    atrasados = apenas_numeros[22:]

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }


# =====================================================
# GERAÇÃO DOS 7 PALPITES (PASSO 2)
# =====================================================

def gerar_7_palpites(historico=None):
    grupos = classificar_numeros(historico)

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
        jogo = (
            _sortear(quentes, q)
            + _sortear(equilibrados, e)
            + _sortear(frios, f)
        )

        jogo = list(set(jogo))

        # Completa até 15 números
        while len(jogo) < NUMEROS_POR_JOGO:
            n = random.choice(universo)
            if n not in jogo:
                jogo.append(n)

        palpites.append({
            "nome": nome,
            "numeros": sorted(jogo)
        })

    # 💤 Palpite 7 – Atrasados
    jogo7 = []

    for grupo in [atrasados, equilibrados, frios, quentes]:
        for n in grupo:
            if len(jogo7) >= NUMEROS_POR_JOGO:
                break
            if n not in jogo7:
                jogo7.append(n)

    palpites.append({
        "nome": "Palpite 7 - Atrasados",
        "numeros": sorted(jogo7)
    })

    return palpites
