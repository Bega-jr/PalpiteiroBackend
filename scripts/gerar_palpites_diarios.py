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
VERSAO = "v9.8.3-discriminativo"

# ======================================================
# POOL
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

    print(f"\n📊 POOL: {len(pool)} números -> {pool}")

    if len(pool) < 15:
        raise ValueError("POOL INVÁLIDO")

    return pool

# ======================================================
# JOGO
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
# VALIDAÇÃO
# ======================================================
def score_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)

    score = 1.0
    score -= abs(7 - pares) * 0.03

    if soma < 165 or soma > 220:
        score -= 0.12

    score -= (max(linhas) - 4) * 0.02

    return max(score, 0.25)

# ======================================================
# DISTÂNCIA
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))

def diversidade_ok(jogo, selecionados):
    return all(distancia(jogo, s) >= 5 for s in selecionados)

# ======================================================
# SCORE FINAL
# ======================================================
def calcular_score_final(nums, base_scores, rec_scores, fator, ultimo_concurso=None):
    chave = tuple(nums)

    base = base_scores.get(chave)
    rec = rec_scores.get(chave)

    if base is None:
        base = np.mean(list(base_scores.values())) if base_scores else 0.5
    if rec is None:
        rec = np.mean(list(rec_scores.values())) if rec_scores else 0.5

    score = (base * 0.6) + (rec * 0.4)

    # ruído controlado (evita empate)
    score *= (1 + np.random.normal(0, 0.025))

    # penalidade leve de repetição com último concurso
    if ultimo_concurso:
        repetidos = len(set(nums) & set(ultimo_concurso))
        score *= (1 - (repetidos / 30))

    score *= score_validacao(nums)

    return max(score, 0.01)

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # ==================================================
    # CONCURSO + FIX DEFINITIVO (LIST vs STRING)
    # ==================================================
    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso,dezenas") \
        .order("concurso", desc=True) \
        .limit(1) \
        .execute().data

    if not concurso:
        raise ValueError("Nenhum concurso encontrado")

    concurso_ref = concurso[0]["concurso"]

    raw_dezenas = concurso[0]["dezenas"]

    # 🔥 FIX CRÍTICO (corrige erro JSON/list)
    if isinstance(raw_dezenas, str):
        ultimo = json.loads(raw_dezenas)
    else:
        ultimo = raw_dezenas

    ultimo = [int(x) for x in ultimo]

    print(f"📌 Concurso: {concurso_ref}")

    # ==================================================
    # POOL
    # ==================================================
    pool = gerar_pool(supabase)

    # ==================================================
    # FATOR
    # ==================================================
    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator: {fator}")

    # ==================================================
    # SCORE BASE
    # ==================================================
    base_scores, rec_scores = calcular_score_combinacoes_reais()

    candidatos = []
    vistos = set()

    # ==================================================
    # GERAÇÃO
    # ==================================================
    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 3000:
            break

        jogo = gerar_jogo(pool)
        key = tuple(jogo)

        if key in vistos:
            continue
        vistos.add(key)

        score = calcular_score_final(
            jogo,
            base_scores,
            rec_scores,
            fator,
            ultimo_concurso=ultimo
        )

        candidatos.append({
            "nums": jogo,
            "score": score
        })

    print(f"✅ candidatos válidos: {len(candidatos)}")

    # ==================================================
    # RANKING
    # ==================================================
    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = []

    for c in candidatos:
        if diversidade_ok(c["nums"], [f["nums"] for f in finais]):
            finais.append(c)

        if len(finais) == QTD_FINAL:
            break

    # fallback
    if len(finais) < QTD_FINAL:
        finais = candidatos[:QTD_FINAL]

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | {p['nums']}")

    print("\n✅ v9.8.3 concluída com sucesso")


if __name__ == "__main__":
    main()
