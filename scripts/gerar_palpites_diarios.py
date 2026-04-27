import sys
import json
import random
from pathlib import Path
from datetime import datetime

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
# CONFIG
# ======================================================
QTD_PALPITES = 7
VERSAO_GERADOR = "v4-memoria-adaptativa"
MAX_TENTATIVAS = 20000

SOMA_MIN = 155
SOMA_MAX = 225
PARES_MIN = 5
PARES_MAX = 10
SEQ_MAX = 6
REPET_MIN = 6
REPET_MAX = 12
LINHA_MIN = 1
LINHA_MAX = 5

SCORE_MIN_BASE = 0.05

# ======================================================
# AUX
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


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
    faixas = [range(1,6), range(6,11), range(11,16), range(16,21), range(21,26)]
    return [sum(1 for n in nums if n in f) for f in faixas]


# ======================================================
# MEMÓRIA
# ======================================================
def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": distribuicao_linhas(nums)
    }


def buscar_memoria(supabase, estrutura):
    res = (
        supabase.table("memoria_cenarios")
        .select("*")
        .eq("soma_faixa", estrutura["soma_faixa"])
        .eq("pares", estrutura["pares"])
        .eq("primos", estrutura["primos"])
        .execute()
    )

    if not res.data:
        return None

    melhor = None
    menor_diff = 999

    for r in res.data:
        diff = sum(abs(a - b) for a, b in zip(r["linhas"], estrutura["linhas"]))
        if diff < menor_diff:
            menor_diff = diff
            melhor = r

    return melhor


def ajustar_score_memoria(score, memoria):
    if not memoria:
        return score

    real = float(memoria.get("score_medio_real", 0))

    if real > 0.6:
        return score * 1.15
    elif real > 0.3:
        return score * 1.05
    elif real < 0.1:
        return score * 0.85

    return score


# ======================================================
# VALIDAÇÃO
# ======================================================
def validar(nums, scores, score_min, ultimos, fator, supabase):
    if len(set(nums)) != 15:
        return False

    pares, soma = calcular_metricas(nums)

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

    score = scores.get(chave, 0)
    score = aplicar_fator_aprendizado(score, fator)

    # 🔥 MEMÓRIA APLICADA AQUI
    estrutura = extrair_estrutura(nums)
    memoria = buscar_memoria(supabase, estrutura)
    score = ajustar_score_memoria(score, memoria)

    return score >= score_min


# ======================================================
# GERAÇÃO
# ======================================================
def gerar(pool, scores, score_min, ultimos, fator, supabase):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores, score_min, ultimos, fator, supabase):
            return nums
    return None


def score_final(nums, scores, fator, supabase):
    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores.get(chave, 0)
    base = aplicar_fator_aprendizado(base, fator)

    estrutura = extrair_estrutura(nums)
    memoria = buscar_memoria(supabase, estrutura)

    return ajustar_score_memoria(base, memoria)


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True).limit(1).execute().data[0]

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

    while len(candidatos) < QTD_PALPITES:
        p = gerar(pool, scores, score_min, ultimos, fator, supabase)

        if p and tuple(p) not in usados:
            usados.add(tuple(p))
            candidatos.append(p)

    ranking = []
    for nums in candidatos:
        ranking.append({
            "numeros": nums,
            "score": score_final(nums, scores, fator, supabase)
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)

    print("\n🏆 RANKING FINAL:")
    for i, r in enumerate(ranking, 1):
        print(f"{i}º | score={round(r['score'],6)} | {r['numeros']}")

    registros = []
    for i, r in enumerate(ranking, 1):
        pares, soma = calcular_metricas(r["numeros"])

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(r["numeros"]),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "score_final": r["score"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Gerador com memória adaptativa finalizado\n")


if __name__ == "__main__":
    main()
