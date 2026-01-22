import sys
import json
import random
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# ======================================================
# Setup base
# ======================================================
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais,
    extrair_metricas_jogo
)

# ======================================================
# Configurações
# ======================================================
VERSAO_GERADOR = "v3.3-debug-diagnostico"
QTD_ESTATISTICOS = 6
MAX_TENTATIVAS = 20000

SOMA_MIN, SOMA_MAX = 150, 230
PARES_MIN, PARES_MAX = 5, 10
SEQ_MAX_GLOBAL = 6
SEQ_MAX_LINHA = 5
REPET_MIN, REPET_MAX = 7, 12
LINHA_MIN, LINHA_MAX = 1, 5

PERCENTIL_INICIAL = 0.20
SCORE_NEUTRO = 0.05

# ======================================================
# Métricas
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


def sequencia_por_linha(nums):
    linhas = {
        1: [n for n in nums if 1 <= n <= 5],
        2: [n for n in nums if 6 <= n <= 10],
        3: [n for n in nums if 11 <= n <= 15],
        4: [n for n in nums if 16 <= n <= 20],
        5: [n for n in nums if 21 <= n <= 25],
    }
    return max(max_sequencia(sorted(v)) if v else 1 for v in linhas.values())


def linhas_ok(nums):
    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]
    return all(LINHA_MIN <= x <= LINHA_MAX for x in linhas)


def finais_ok(nums):
    finais = defaultdict(int)
    for n in nums:
        finais[n % 10] += 1
    return max(finais.values()) <= 3


def repeticao_ok(nums, ultimos):
    return REPET_MIN <= len(set(nums) & set(ultimos)) <= REPET_MAX


# ======================================================
# Validação com DEBUG
# ======================================================
def validar(nums, scores, score_min, ultimos, fator, debug):
    falhas = []

    pares, soma = calcular_metricas(nums)
    if not (SOMA_MIN <= soma <= SOMA_MAX):
        falhas.append("soma")

    if not (PARES_MIN <= pares <= PARES_MAX):
        falhas.append("pares")

    if max_sequencia(nums) > SEQ_MAX_GLOBAL:
        falhas.append("sequencia_global")

    if sequencia_por_linha(nums) > SEQ_MAX_LINHA:
        falhas.append("sequencia_linha")

    if not linhas_ok(nums):
        falhas.append("linhas")

    if not finais_ok(nums):
        falhas.append("finais")

    if not repeticao_ok(nums, ultimos):
        falhas.append("repeticao")

    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores.get(chave)
    score_final = (base if base is not None else SCORE_NEUTRO) * fator

    if score_final < score_min:
        falhas.append("score")

    # DEBUG sempre registra TODAS as falhas
    for f in falhas:
        debug[f] += 1

    return len(falhas) == 0


# ======================================================
# Geração
# ======================================================
def gerar_palpite(pool, scores, score_min, ultimos, fator, debug):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores, score_min, ultimos, fator, debug):
            return nums
    return None


# ======================================================
# Execução principal
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
    print(f"🧠 Fator de aprendizado global: {fator}")

    scores = calcular_score_combinacoes_reais()
    valores = sorted(scores.values(), reverse=True)
    score_min = valores[int(len(valores) * PERCENTIL_INICIAL)] if valores else 0.03

    print(f"📊 Score mínimo aplicado: {round(score_min,4)}")

    debug = defaultdict(int)

    fixo = gerar_palpite(pool, scores, score_min, ultimos, fator, debug)

    if not fixo:
        print("\n❌ NENHUM PALPITE GERADO")
        print("\n📉 RELATÓRIO DE BLOQUEIO POR REGRA:")
        total = sum(debug.values())
        for k, v in sorted(debug.items(), key=lambda x: -x[1]):
            pct = (v / total * 100) if total else 0
            print(f" - {k:20}: {v:6} ({pct:.1f}%)")
        print("\n⚠️ Ajuste recomendado: regra com maior percentual")
        return

    print("✅ Palpite fixo gerado com sucesso")
    print(fixo)


if __name__ == "__main__":
    main()



