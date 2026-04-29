import sys
import random
import json
import numpy as np
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

# ======================================================
# CONFIG
# ======================================================
QTD_FINAL = 7
MAX_TENTATIVAS = 60000
VERSAO = "v9.8.2-estavel"

# ======================================================
# POOL (BLINDADO)
# ======================================================
def gerar_pool(supabase):
    data = supabase.table("estatisticas_numeros") \
        .select("numero") \
        .execute().data

    pool = sorted(set(
        int(r["numero"])
        for r in data
        if r.get("numero") is not None
    ))

    print(f"\n📊 POOL RAW SIZE: {len(data)}")
    print(f"📊 POOL FINAL SIZE: {len(pool)}")
    print(f"📊 POOL: {pool}")

    if len(pool) < 15:
        raise ValueError("POOL CORROMPIDO")

    return pool

# ======================================================
# GERAÇÃO
# ======================================================
def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))

# ======================================================
# MÉTRICAS
# ======================================================
def calcular_metricas(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)

    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]

    return pares, soma, linhas

# ======================================================
# VALIDAÇÃO SUAVE
# ======================================================
def score_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)

    score = 1.0
    score -= abs(7 - pares) * 0.03

    if soma < 165 or soma > 220:
        score -= 0.15

    score -= (max(linhas) - 4) * 0.02

    return max(score, 0.2)

# ======================================================
# SCORE FINAL
# ======================================================
def calcular_score_final(nums, base_scores, rec_scores, fator):
    chave = tuple(nums)

    base = base_scores.get(chave)
    rec = rec_scores.get(chave)

    if base is None:
        base = np.mean(list(base_scores.values())) if base_scores else 0.5
    if rec is None:
        rec = np.mean(list(rec_scores.values())) if rec_scores else 0.5

    score = (base * 0.6) + (rec * 0.4)

    # ruído leve (evita empate)
    score *= (1 + np.random.normal(0, 0.03))

    return score * fator * score_validacao(nums)

# ======================================================
# DIVERSIDADE
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))


def diversidade_ok(jogo, selecionados):
    return all(distancia(jogo, s) >= 5 for s in selecionados)

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    concurso_ref = concurso[0]["concurso"]
    print(f"📌 Concurso: {concurso_ref}")

    pool = gerar_pool(supabase)

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator: {fator}")

    base_scores, rec_scores = calcular_score_combinacoes_reais()

    candidatos = []
    vistos = set()

    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 3000:
            break

        jogo = gerar_jogo(pool)
        key = tuple(jogo)

        if key in vistos:
            continue
        vistos.add(key)

        score = calcular_score_final(jogo, base_scores, rec_scores, fator)

        candidatos.append({
            "nums": jogo,
            "score": score
        })

    print(f"✅ candidatos: {len(candidatos)}")

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = []

    for c in candidatos:
        if diversidade_ok(c["nums"], [f["nums"] for f in finais]):
            finais.append(c)

        if len(finais) == QTD_FINAL:
            break

    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(i, p["score"], p["nums"])

    print("\n✅ v9.8.2 concluída")


if __name__ == "__main__":
    main()
