import sys
import json
import random
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais,
    extrair_metricas_jogo
)

VERSAO_GERADOR = "v3.4-score-ponderado-real"
QTD_ESTATISTICOS = 6
MAX_TENTATIVAS = 25000

SOMA_MIN, SOMA_MAX = 150, 230
PARES_MIN, PARES_MAX = 5, 10
SEQ_MAX = 7

PESO_LINHAS = 0.90
PESO_FINAIS = 0.85
PESO_REPETICAO = 0.85
PESO_SCORE_REAL = 1.00

SCORE_CORTE = 0.05
SCORE_NEUTRO = 0.04


# ======================================================
def max_sequencia(nums):
    atual = seq = 1
    for i in range(1, len(nums)):
        atual = atual + 1 if nums[i] == nums[i-1] + 1 else 1
        seq = max(seq, atual)
    return seq


def penalidade_linhas(nums):
    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]
    return PESO_LINHAS if max(linhas) >= 6 else 1.0


def penalidade_finais(nums):
    finais = defaultdict(int)
    for n in nums:
        finais[n % 10] += 1
    return PESO_FINAIS if max(finais.values()) >= 5 else 1.0


def penalidade_repeticao(nums, ultimos):
    r = len(set(nums) & set(ultimos))
    return PESO_REPETICAO if r < 6 or r > 13 else 1.0


# ======================================================
def calcular_score_final(nums, scores_reais, fator, ultimos):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return 0
    if not (PARES_MIN <= pares <= PARES_MAX):
        return 0
    if max_sequencia(nums) > SEQ_MAX:
        return 0

    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores_reais.get(chave, SCORE_NEUTRO)
    score = base * fator * PESO_SCORE_REAL

    score *= penalidade_linhas(nums)
    score *= penalidade_finais(nums)
    score *= penalidade_repeticao(nums, ultimos)

    return round(score, 6)


# ======================================================
def gerar_palpite(pool, scores, fator, ultimos):
    melhor = None
    melhor_score = 0

    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        score = calcular_score_final(nums, scores, fator, ultimos)

        if score > melhor_score:
            melhor = nums
            melhor_score = score

        if score >= SCORE_CORTE:
            return nums, score

    return melhor, melhor_score


# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    concurso = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    ).data[0]

    ultimos = list(map(int, concurso["dezenas"]))
    concurso_ref = concurso["concurso"]

    pool = [
        n["numero"] for n in
        supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(30)
        .execute().data
    ]

    fator = obter_fator_aprendizado_global()["fator"]
    scores = calcular_score_combinacoes_reais()

    fixo, score = gerar_palpite(pool, scores, fator, ultimos)

    print(f"🎯 Palpite fixo gerado | score={score}")
    print(fixo)


if __name__ == "__main__":
    main()



