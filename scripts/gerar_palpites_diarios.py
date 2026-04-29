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
VERSAO = "v9.6-real-estavel"

# ======================================================
# POOL LIMPO E ESTÁVEL
# ======================================================
def gerar_pool(supabase):
    data = supabase.table("estatisticas_numeros") \
        .select("numero") \
        .order("score", desc=True) \
        .limit(60) \
        .execute().data

    return sorted(set(r["numero"] for r in data))

# ======================================================
# GERAÇÃO GARANTIDA (SEM DUPLICADOS INTERNOS)
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
# VALIDAÇÃO PROBABILÍSTICA (NÃO BINÁRIA)
# ======================================================
def score_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)

    score = 1.0

    # pares ideal ~7
    score -= abs(7 - pares) * 0.04

    # soma ideal faixa central
    if soma < 165 or soma > 220:
        score -= 0.2

    # distribuição linhas
    score -= (max(linhas) - 4) * 0.03

    return max(score, 0.1)

# ======================================================
# DIVERSIDADE REAL
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))


def diversidade_ok(jogo, selecionados):
    return all(distancia(jogo, s) >= 5 for s in selecionados)

# ======================================================
# NORMALIZAÇÃO DE SCORE KEY (CORREÇÃO CRÍTICA)
# ======================================================
def normalizar_chave(nums):
    return tuple(sorted(nums))

# ======================================================
# SCORE FINAL CONSISTENTE
# ======================================================
def calcular_score_final(nums, base_scores, rec_scores, fator):
    chave = normalizar_chave(nums)

    base = base_scores.get(chave)
    rec = rec_scores.get(chave)

    # fallback inteligente (NUNCA zero)
    if base is None:
        base = np.mean(list(base_scores.values())) if base_scores else 0.5
    if rec is None:
        rec = np.mean(list(rec_scores.values())) if rec_scores else 0.5

    score = (base * 0.55) + (rec * 0.45)

    return score * fator * score_validacao(nums)

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

    raw_scores = calcular_score_combinacoes_reais()

    # compatibilidade total (dict ou tuple)
    if isinstance(raw_scores, dict):
        base_scores = raw_scores.get("base", {})
        rec_scores = raw_scores.get("recencia", {})
    else:
        base_scores, rec_scores = raw_scores[:2]

    candidatos = []
    vistos = set()

    # ==================================================
    # GERAÇÃO PRINCIPAL
    # ==================================================
    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 2500:
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

    # ==================================================
    # SEM FALLBACK LIXO (CORREÇÃO CRÍTICA)
    # ==================================================
    candidatos = [c for c in candidatos if c["score"] > 0]

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

    # fallback inteligente (NÃO LIXO)
    if len(finais) < QTD_FINAL:
        finais = candidatos[:QTD_FINAL]

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | {p['nums']}")

    # ==================================================
    # SAVE
    # ==================================================
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

    print("\n✅ v9.6 executada com estabilidade REAL\n")


if __name__ == "__main__":
    main()
