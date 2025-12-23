import random
import datetime
import csv
from collections import Counter
from functools import lru_cache
from pathlib import Path

# =====================================================
# CONFIGURAÇÕES GERAIS
# =====================================================

TOTAL_NUMEROS = 25
NUMEROS_POR_JOGO = 15

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CSV_PATH = BASE_DIR / "data" / "historico_lotofacil.csv"

# =====================================================
# FUNÇÃO AUXILIAR
# =====================================================

def _sortear(grupo, qtd):
    if not grupo:
        return []
    return random.sample(grupo, min(qtd, len(grupo)))

# =====================================================
# LEITURA DO HISTÓRICO (CSV)
# =====================================================

@lru_cache(maxsize=1)
def carregar_historico():
    """
    Carrega o histórico real da Lotofácil a partir do CSV.
    Usa cache para não reler o arquivo a cada request.
    """
    historico = []

    if not CSV_PATH.exists():
        print("⚠️ CSV não encontrado, usando fallback aleatório")
        return historico

    try:
        with open(CSV_PATH, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                numeros = [int(n) for n in row if n.isdigit()]
                if len(numeros) == 15:
                    historico.append(numeros)
    except Exception as e:
        print("❌ Erro ao ler CSV:", e)
        return []

    return historico

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

    # Frequência padrão caso histórico esteja vazio
    frequencias = {n: contador.get(n, 0) for n in todos}

    ordenados = sorted(frequencias.items(), key=lambda x: x[1], reverse=True)
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
    historico = carregar_historico()
    grupos = classificar_numeros(historico)

    jogo = (
        _sortear(grupos["quentes"], 6) +
        _sortear(grupos["equilibrados"], 5) +
        _sortear(grupos["frios"], 4)
    )

    jogo = list(set(jogo))
    universo = list(range(1, TOTAL_NUMEROS + 1))

    # Completa até 15 números
    while len(jogo) < NUMEROS_POR_JOGO:
        n = random.choice(universo)
        if n not in jogo:
            jogo.append(n)

    return sorted(jogo)

def gerar_palpite_fixo():
    """
    Palpite fixo público – atualizado automaticamente 1x por dia
    """
    hoje = datetime.date.today().isoformat()
    return _palpite_fixo_cache(hoje)

# =====================================================
# GERAÇÃO DOS 7 PALPITES (PASSO 2)
# =====================================================

def gerar_7_palpites(historico=None):
    if historico is None:
        historico = carregar_historico()

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

        while len(jogo) < NUMEROS_POR_JOGO:
            n = random.choice(universo)
            if n not in jogo:
                jogo.append(n)

        palpites.append({
            "nome": nome,
            "numeros": sorted(jogo)
        })

    # Palpite 7 – Atrasados
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
