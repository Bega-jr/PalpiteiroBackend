import random
import datetime
from functools import lru_cache

from app.services.estatisticas_services import obter_estatisticas_base
from app.services.estatisticas_validator import filtrar_jogos_validos

# =====================================================
# CONFIGURAÇÕES
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15


# =====================================================
# CLASSIFICAÇÃO BASEADA EM DADOS REAIS
# =====================================================

def classificar_numeros():
    """
    Classifica números da Lotofácil usando estatísticas reais.
    NÃO lança exceção — retorna None se falhar.
    """

    estatisticas = obter_estatisticas_base()

    if estatisticas is None or estatisticas.empty:
        return None

    quentes = estatisticas.head(8)["numero"].tolist()
    equilibrados = estatisticas.iloc[8:16]["numero"].tolist()
    frios = estatisticas.iloc[16:22]["numero"].tolist()
    atrasados = (
        estatisticas
        .sort_values("atraso", ascending=False)
        .head(8)["numero"]
        .tolist()
    )

    if not all([quentes, equilibrados, frios, atrasados]):
        return None

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
    grupos = classificar_numeros()
    if not grupos:
        return None

    jogo = (
        random.sample(grupos["quentes"], 6) +
        random.sample(grupos["equilibrados"], 5) +
        random.sample(grupos["frios"], 4)
    )

    if len(set(jogo)) != NUMEROS_POR_JOGO:
        return None

    return sorted(jogo)


def gerar_palpite_fixo():
    """
    Gera 1 palpite fixo por dia.
    Se estatísticas não estiverem disponíveis, retorna None.
    """
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)


# =====================================================
# 7 PALPITES ESTATÍSTICOS COM FECHAMENTO
# =====================================================

def gerar_7_palpites():
    grupos = classificar_numeros()
    if not grupos:
        return []

    configuracoes = [
        ("Palpite 1 - Muito Quente", 8, 5, 2),
        ("Palpite 2 - Quente", 7, 6, 2),
        ("Palpite 3 - Equilibrado Quente", 5, 7, 3),
        ("Palpite 4 - Equilibrado Frio", 4, 6, 5),
        ("Palpite 5 - Frio", 3, 4, 8),
        ("Palpite 6 - Muito Frio", 2, 3, 10),
    ]

    palpites = []

    for nome, q, e, f in configuracoes:
        try:
            jogo = (
                random.sample(grupos["quentes"], q) +
                random.sample(grupos["equilibrados"], e) +
                random.sample(grupos["frios"], f)
            )

            jogo = sorted(set(jogo))

            if len(jogo) != NUMEROS_POR_JOGO:
                continue

            palpites.append({
                "nome": nome,
                "numeros": jogo
            })

        except ValueError:
            continue

    # =================================================
    # Palpite 7 – Fechamento Equilibrado/Atrasados
    # =================================================

    jogo7 = []
    for grupo in [grupos["atrasados"], grupos["equilibrados"], grupos["frios"], grupos["quentes"]]:
        for n in grupo:
            if len(jogo7) < NUMEROS_POR_JOGO and n not in jogo7:
                jogo7.append(n)

    if len(jogo7) == NUMEROS_POR_JOGO:
        palpites.append({
            "nome": "Palpite 7 - Atrasados",
            "numeros": sorted(jogo7)
        })

    # =================================================
    # VALIDAÇÃO FINAL (SEM FALLBACK)
    # =================================================

    jogos_validos = filtrar_jogos_validos(
        [p["numeros"] for p in palpites]
    )

    # Mantém apenas palpites aprovados
    palpites_filtrados = [
        p for p in palpites
        if p["numeros"] in jogos_validos
    ]

    return palpites_filtrados
