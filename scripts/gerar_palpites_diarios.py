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
from app.services.roi_service import (
    obter_probabilidades_reais,
    calcular_roi_real
)

# ======================================================
# CONFIG
# ======================================================
QTD_FINAL = 7
POOL_SIZE = 22
MAX_TENTATIVAS = 40000
VERSAO = "v6-memoria-ativa"

ROI_MIN = -0.05

# ======================================================
# AUX
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }


def buscar_memoria(supabase, estrutura):
    res = (
        supabase
        .table("memoria_cenarios")
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


def validar(nums):
    if len(set(nums)) != 15:
        return False

    pares, soma = calcular_metricas(nums)

    if not (150 <= soma <= 230):
        return False

    if not (4 <= pares <= 11):
        return False

    return True


# ======================================================
# SCORE + MEMÓRIA
# ======================================================
def score_final(nums, scores, fator, memoria):
    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores.get(chave, 0)
    score = aplicar_fator_aprendizado(base, fator)

    # 🔥 AJUSTE POR MEMÓRIA
    if memoria:
        score_real = float(memoria.get("score_medio_real", 0))

        if score_real > 0:
            score *= (1 + score_real)

        # penaliza cenários ruins
        if score_real < 0.05:
            score *= 0.7

    return score


# ======================================================
# DIVERSIFICAÇÃO
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))


def diversificar(candidatos):
    selecionados = []

    for c in candidatos:
        if not selecionados:
            selecionados.append(c)
            continue

        if all(distancia(c["nums"], s["nums"]) >= 6 for s in selecionados):
            selecionados.append(c)

        if len(selecionados) >= QTD_FINAL:
            break

    return selecionados


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
        .limit(1).execute().data[0]

    concurso_ref = concurso["concurso"]

    pool = [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(POOL_SIZE)
        .execute().data
    ]

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()

    probs_reais = obter_probabilidades_reais(VERSAO)

    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))

        if not validar(nums):
            continue

        estrutura = extrair_estrutura(nums)
        memoria = buscar_memoria(supabase, estrutura)

        score = score_final(nums, scores, fator, memoria)

        if probs_reais:
            roi = calcular_roi_real(score, probs_reais)
        else:
            roi = score * 0.5  # fallback simples

        candidatos.append({
            "nums": nums,
            "score": score,
            "roi": roi
        })

    if not candidatos:
        print("❌ Nenhum candidato válido")
        return

    print(f"📊 {len(candidatos)} candidatos gerados")

    candidatos.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)

    finais = diversificar(candidatos)

    print("\n🏆 RANKING FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | ROI={round(p['roi'],4)} | score={round(p['score'],4)} | {p['nums']}")

    # salvar
    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    registros = []

    for i, p in enumerate(finais, 1):
        pares, soma = calcular_metricas(p["nums"])

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
                "score": p["score"],
                "roi": p["roi"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Gerador com memória ATIVA finalizado\n")


if __name__ == "__main__":
    main()
