import random
import datetime
from collections import Counter
from functools import lru_cache

from app.services.estatisticas_validator import validar_jogo
from app.services.estatisticas_services import obter_estatisticas_base

# =====================================================
# CONFIGURAÇÕES
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15
MAX_TENTATIVAS = 50


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

def classificar_numeros():
    """
    Classifica números com base no histórico real.
    Se falhar, usa fallback seguro.
    """
    try:
        estatisticas = obter_estatisticas_base()

        if estatisticas is None or estatisticas.empty:
            raise ValueError("Estatísticas vazias")

        numeros_ordenados = estatisticas["numero"].tolist()

    except Exception:
        # 🔥 fallback absoluto
        numeros_ordenados = list(range(1, TOTAL_NUMEROS + 1))

    quentes = numeros_ordenados[:8]
    equilibrados = numeros_ordenados[8:16]
    frios = numeros_ordenados[16:22]
    atrasados = numeros_ordenados[22:]

    return {
        "quentes": quentes,
        "equilibrados": equilibrados,
        "frios": frios,
        "atrasados": atrasados
    }


# =====================================================
# PALPITE FIXO DIÁRIO (COM CACHE + VALIDAÇÃO)
# =====================================================

@lru_cache(maxsize=1)
def _palpite_fixo_cache(data):
    grupos = classificar_numeros()
    universo = list(range(1, TOTAL_NUMEROS + 1))

    for _ in range(MAX_TENTATIVAS):
        jogo = (
            _sortear(grupos["quentes"], 6) +
            _sortear(grupos["equilibrados"], 5) +
            _sortear(grupos["frios"], 4)
        )

        jogo = list(set(jogo))

        while len(jogo) < NUMEROS_POR_JOGO:
            n = random.choice(universo)
            if n not in jogo:
                jogo.append(n)

        jogo = sorted(jogo)

        # ✅ validação estatística
        resultado = validar_jogo(jogo)
        if resultado["aprovado"]:
            return jogo

    # 🔥 fallback final (nunca quebra)
    return sorted(random.sample(universo, NUMEROS_POR_JOGO))


def gerar_palpite_fixo():
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# GERAÇÃO DOS 7 PALPITES (COM VALIDAÇÃO)
# =====================================================

def gerar_7_palpites():
    grupos = classificar_numeros()

    quentes = grupos["quentes"]
    equilibrados = grupos["equilibrados"]
    frios = grupos["frios"]
    atrasados = grupos["atrasados"]

    configuracoes = [
        ("Palpite 1 - Muito Quente", 8, 5, 2),
        ("Palpite 2 - Quente", 7, 6, 2),
        ("Palpite 3 - Equilibrado Quente", 5, 7, 3),
        ("Palpite 4 - Equilibrado Frio", 4, 6, 5),
        ("Palpite 5 - Frio", 3, 4, 8),
        ("Palpite 6 - Muito Frio", 2, 3, 10),
    ]

    universo = list(range(1, TOTAL_NUMEROS + 1))
    palpites = []

    for nome, q, e, f in configuracoes:
        for _ in range(MAX_TENTATIVAS):
            jogo = (
                _sortear(quentes, q)
                + _sortear(equilibrados, e)
                + _sortear(frios, f)
            )

            jogo = list(set(jogo))

            while len(jogo) < NUMEROS_POR_JOGO:
                n = random.choice(universo)
                if n not in jogo:
                    jogo.append(n)

            jogo = sorted(jogo)

            if validar_jogo(jogo)["aprovado"]:
                palpites.append({
                    "nome": nome,
                    "numeros": jogo
                })
                break

    # -------------------------------------------------
    # Palpite 7 – Atrasados (mais permissivo)
    # -------------------------------------------------

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

