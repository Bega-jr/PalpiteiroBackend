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
MAX_TENTATIVAS = 40000
VERSAO = "v9.4-inteligente-diversificado"

# ======================================================
# UTIL
# ======================================================
def gerar_pool(supabase):
    return [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(25)
        .execute().data
    ]

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
# VALIDAÇÃO DINÂMICA (ANTI TRAVAMENTO)
# ======================================================
def validar(nums, params):
    pares, soma, linhas = calcular_metricas(nums)

    if not (params["soma_min"] <= soma <= params["soma_max"]):
        return False

    if not (params["pares_min"] <= pares <= params["pares_max"]):
        return False

    if max(linhas) > 5:
        return False

    return True

# ======================================================
# PARÂMETROS DINÂMICOS
# ======================================================
def parametros_dinamicos():
    return {
        "soma_min": 160,
        "soma_max": 225,
        "pares_min": 5,
        "pares_max": 10
    }

# ======================================================
# DIVERSIDADE ENTRE JOGOS
# ======================================================
def distancia(jogo1, jogo2):
    return len(set(jogo1) ^ set(jogo2))

def diversidade_ok(jogo, selecionados, min_dist=5):
    for s in selecionados:
        if distancia(jogo, s) < min_dist:
            return False
    return True

# ======================================================
# SCORE FINAL (MULTICRITÉRIO)
# ======================================================
def calcular_score_final(nums, scores, fator):
    chave = (
        round(sum(nums)/10)*10,
        sum(n % 2 == 0 for n in nums),
        sum(n in {2,3,5,7,11,13,17,19,23} for n in nums),
        tuple([
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ])
    )

    base = scores.get(chave, 0)

    # bônus leve por distribuição equilibrada
    pares = sum(n % 2 == 0 for n in nums)
    bonus = 1 - abs(7 - pares) * 0.05

    return base * fator * bonus

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # concurso
    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    if not concurso:
        print("❌ Sem concurso")
        return

    concurso_ref = concurso[0]["concurso"]
    print(f"📌 Concurso referência: {concurso_ref}")

    # parâmetros
    params = parametros_dinamicos()
    print(f"📊 Parâmetros: {params}")

    pool = gerar_pool(supabase)
    print(f"📊 Pool size: {len(pool)}")

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()

    candidatos = []
    vistos = set()

    # ==================================================
    # GERAÇÃO
    # ==================================================
    for _ in range(MAX_TENTATIVAS):
        jogo = gerar_jogo(pool)

        key = tuple(jogo)
        if key in vistos:
            continue
        vistos.add(key)

        if not validar(jogo, params):
            continue

        score = calcular_score_final(jogo, scores, fator)

        candidatos.append({
            "nums": jogo,
            "score": score
        })

    if not candidatos:
        print("❌ Nenhum candidato gerado")
        return

    print(f"✅ {len(candidatos)} candidatos válidos")

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

    # ==================================================
    # SAVE (SEGURO)
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

    print("\n✅ Geração v9.4 concluída com sucesso\n")


if __name__ == "__main__":
    main()
