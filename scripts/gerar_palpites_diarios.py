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
MAX_TENTATIVAS = 50000
VERSAO = "v9.5-adaptativo-estavel"

# ======================================================
# UTIL
# ======================================================
def gerar_pool(supabase):
    data = supabase.table("estatisticas_numeros") \
        .select("numero, score") \
        .order("score", desc=True) \
        .limit(50) \
        .execute().data

    return [r["numero"] for r in data]


def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))


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
# PARAMETROS ADAPTATIVOS
# ======================================================
def parametros_dinamicos(n_fail=0):
    relax = min(n_fail * 2, 15)

    return {
        "soma_min": 160 - relax,
        "soma_max": 225 + relax,
        "pares_min": max(4, 5 - n_fail),
        "pares_max": min(11, 10 + n_fail),
        "min_score": max(0.45, 0.65 - n_fail * 0.03)
    }

# ======================================================
# DIVERSIDADE
# ======================================================
def distancia(j1, j2):
    return len(set(j1) ^ set(j2))


def diversidade_ok(jogo, selecionados):
    for s in selecionados:
        if distancia(jogo, s) < 5:
            return False
    return True

# ======================================================
# SCORE DINÂMICO (CORE V9.5)
# ======================================================
def calcular_score_final(nums, base_scores, recencia_scores, fator):
    chave = tuple(nums)

    base = base_scores.get(chave, 0)
    rec = recencia_scores.get(chave, 0)

    score = (base * 0.6) + (rec * 0.4)

    pares = sum(n % 2 == 0 for n in nums)
    bonus = 1 - abs(7 - pares) * 0.04

    return score * fator * bonus

# ======================================================
# VALIDACAO
# ======================================================
def validar(nums, params):
    pares, soma, linhas = calcular_metricas(nums)

    if not (params["soma_min"] <= soma <= params["soma_max"]):
        return False

    if not (params["pares_min"] <= pares <= params["pares_max"]):
        return False

    if max(linhas) > 6:
        return False

    return True

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

    if not concurso:
        print("❌ Sem concurso")
        return

    concurso_ref = concurso[0]["concurso"]
    print(f"📌 Concurso referência: {concurso_ref}")

    pool = gerar_pool(supabase)
    print(f"📊 Pool size: {len(pool)}")

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores_base, scores_recencia = calcular_score_combinacoes_reais(ultimos=1000)

    candidatos = []
    vistos = set()
    falhas = 0

    params = parametros_dinamicos(falhas)

    # ==================================================
    # GERAÇÃO
    # ==================================================
    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 2000:
            break

        jogo = gerar_jogo(pool)

        key = tuple(jogo)
        if key in vistos:
            continue
        vistos.add(key)

        if not validar(jogo, params):
            falhas += 1
            params = parametros_dinamicos(falhas)
            continue

        score = calcular_score_final(
            jogo,
            scores_base,
            scores_recencia,
            fator
        )

        if score < params["min_score"]:
            continue

        candidatos.append({
            "nums": jogo,
            "score": score
        })

    # ==================================================
    # FALLBACK (GARANTIA ZERO FAIL)
    # ==================================================
    if not candidatos:
        print("⚠️ Fallback ativado (relaxamento total)")

        for _ in range(3000):
            jogo = gerar_jogo(pool)

            score = calcular_score_final(
                jogo,
                scores_base,
                scores_recencia,
                fator
            )

            candidatos.append({
                "nums": jogo,
                "score": score
            })

    print(f"✅ Candidatos: {len(candidatos)}")

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

    if len(finais) < QTD_FINAL:
        finais = candidatos[:QTD_FINAL]

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | {p['nums']}")

    # ======================================================
    # SAVE
    # ======================================================
    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    registros = []

    for i, p in enumerate(finais, 1):
        pares, soma, _ = calcular_metricas(p["nums"])

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(p["nums"]),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO,
                "score": p["score"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ v9.5 concluída com estabilidade total\n")


if __name__ == "__main__":
    main()
