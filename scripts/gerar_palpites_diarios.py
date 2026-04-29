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
MAX_TENTATIVAS = 70000
VERSAO = "v9.8-probabilistico"

# ======================================================
# POOL ESTÁVEL
# ======================================================
def gerar_pool(supabase):
    data = supabase.table("estatisticas_numeros") \
        .select("numero") \
        .order("score", desc=True) \
        .limit(80) \
        .execute().data

    pool = sorted({r["numero"] for r in data if isinstance(r.get("numero"), int)})

    if len(pool) < 15:
        raise ValueError(f"POOL INVÁLIDO: apenas {len(pool)} números")

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
# SCORE BASE (NORMALIZADO)
# ======================================================
def score_base(nums, base_scores, rec_scores):
    chave = tuple(nums)

    base = base_scores.get(chave)
    rec = rec_scores.get(chave)

    if base is None:
        base = np.mean(list(base_scores.values())) if base_scores else 0.5
    if rec is None:
        rec = np.mean(list(rec_scores.values())) if rec_scores else 0.5

    return (base * 0.6) + (rec * 0.4)

# ======================================================
# SCORE PROBABILÍSTICO (NÚCLEO v9.8)
# ======================================================
def score_probabilistico(score):
    # transforma score em distribuição (evita empate)
    ruido = np.random.normal(0, 0.05)
    return score + ruido

# ======================================================
# VALIDAÇÃO COMO PESO (NÃO FILTRO)
# ======================================================
def peso_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)

    peso = 1.0

    peso -= abs(7 - pares) * 0.03

    if soma < 165 or soma > 220:
        peso -= 0.15

    peso -= (max(linhas) - 4) * 0.02

    return max(peso, 0.2)

# ======================================================
# DIVERSIDADE
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))


def diversidade_ok(jogo, selecionados):
    return all(distancia(jogo, s) >= 5 for s in selecionados)

# ======================================================
# NORMALIZAÇÃO
# ======================================================
def normalizar(nums):
    return tuple(sorted(nums))

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

    raw = calcular_score_combinacoes_reais()

    if isinstance(raw, dict):
        base_scores = raw.get("base", {})
        rec_scores = raw.get("recencia", {})
    else:
        base_scores, rec_scores = raw[:2]

    candidatos = []
    vistos = set()

    # ==================================================
    # GERAÇÃO
    # ==================================================
    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 3000:
            break

        jogo = gerar_jogo(pool)
        key = normalizar(jogo)

        if key in vistos:
            continue
        vistos.add(key)

        base = score_base(jogo, base_scores, rec_scores)

        # probabilístico (NÚCLEO v9.8)
        score = score_probabilistico(base)

        # fator aprendizado
        score *= fator

        # peso de validação (não bloqueia, só ajusta ranking)
        score *= peso_validacao(jogo)

        candidatos.append({
            "nums": jogo,
            "score": score
        })

    print(f"✅ candidatos: {len(candidatos)}")

    # ==================================================
    # RANKING POR PERCENTIL (NOVA LÓGICA)
    # ==================================================
    scores = np.array([c["score"] for c in candidatos])

    # evita divisão por zero
    if len(scores) == 0:
        print("❌ sem candidatos")
        return

    percentis = np.argsort(np.argsort(scores))

    for i, c in enumerate(candidatos):
        c["score"] = percentis[i] / len(scores)

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    # ==================================================
    # SELEÇÃO FINAL
    # ==================================================
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
                "score": float(p["score"])
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ v9.8 executada com modelo probabilístico\n")


if __name__ == "__main__":
    main()
