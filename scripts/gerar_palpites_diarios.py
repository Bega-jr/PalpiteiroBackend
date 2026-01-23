import sys
import json
import random
from pathlib import Path
from datetime import datetime

# ======================================================
# Setup
# ======================================================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import (
    obter_fator_aprendizado_global,
    aplicar_fator_aprendizado
)
from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais,
    extrair_metricas_jogo
)

# ======================================================
# Configurações
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v3.8-score-real-ranking-safe"
MAX_TENTATIVAS_PALPITE = 15000
MAX_CICLOS_GERACAO = 50000

SOMA_MIN = 155
SOMA_MAX = 225
PARES_MIN = 5
PARES_MAX = 10
SEQ_MAX = 5
REPET_MIN = 7
REPET_MAX = 12
LINHA_MIN = 1
LINHA_MAX = 5
SCORE_MIN_BASE = 0.1

# ======================================================
# Auxiliares
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    impares = 15 - pares
    soma = sum(nums)
    return pares, impares, soma


def max_sequencia(nums):
    atual = seq = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 1
    return seq


def distribuicao_linhas(nums):
    faixas = [
        range(1, 6),
        range(6, 11),
        range(11, 16),
        range(16, 21),
        range(21, 26),
    ]
    return [sum(1 for n in nums if n in f) for f in faixas]


def validar(nums, scores, score_min, ultimos, fator):
    if len(set(nums)) != 15:
        return False

    pares, _, soma = calcular_metricas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
    if not (PARES_MIN <= pares <= PARES_MAX):
        return False
    if max_sequencia(nums) > SEQ_MAX:
        return False
    if not all(LINHA_MIN <= x <= LINHA_MAX for x in distribuicao_linhas(nums)):
        return False

    repetidos = len(set(nums) & set(ultimos))
    if not (REPET_MIN <= repetidos <= REPET_MAX):
        return False

    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    score_base = scores.get(chave, 0)
    score_final = aplicar_fator_aprendizado(score_base, fator)

    return score_final >= score_min


def gerar_palpite(pool, scores, score_min, ultimos, fator):
    for _ in range(MAX_TENTATIVAS_PALPITE):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores, score_min, ultimos, fator):
            return nums
    return None


def score_palpite(nums, scores, fator):
    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )
    return aplicar_fator_aprendizado(scores.get(chave, 0), fator)

# ======================================================
# Main
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1).execute().data[0]

    concurso_ref = concurso["concurso"]
    ultimos = list(map(int, concurso["dezenas"]))

    pool = [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(20).execute().data
    ]

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()
    score_min = SCORE_MIN_BASE
    print(f"📊 Score mínimo: {score_min}")

    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    candidatos = []
    usados = set()
    ciclos = 0

    while len(candidatos) < QTD_PALPITES and ciclos < MAX_CICLOS_GERACAO:
        ciclos += 1

        p = gerar_palpite(pool, scores, score_min, ultimos, fator)
        if not p:
            continue

        t = tuple(p)
        if t in usados:
            continue

        usados.add(t)
        candidatos.append(p)

        if ciclos % 5000 == 0:
            print(f"⏳ Tentativas: {ciclos} | Gerados: {len(candidatos)}")

    if not candidatos:
        print("❌ Falha crítica: nenhum palpite viável gerado")
        return

    if len(candidatos) < QTD_PALPITES:
        print(f"⚠️ Apenas {len(candidatos)} palpites válidos gerados")

    ranking = [
        {
            "numeros": nums,
            "score": score_palpite(nums, scores, fator)
        }
        for nums in candidatos
    ]

    ranking.sort(key=lambda x: x["score"], reverse=True)

    print("\n🏆 RANKING FINAL:")
    for i, r in enumerate(ranking, 1):
        print(f"{i}º | score={round(r['score'],6)} | {r['numeros']}")

    registros = []
    for i, r in enumerate(ranking, 1):
        pares, impares, soma = calcular_metricas(r["numeros"])
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(r["numeros"]),
            "pares": pares,
            "impares": impares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "aprendizado": "v3-global",
                "score_final": r["score"],
                "ranking": i
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Gerador finalizado com ranking persistido corretamente\n")


if __name__ == "__main__":
    main()


