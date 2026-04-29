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
POOL_SIZE = 20
MAX_TENTATIVAS = 40000
VERSAO = "v8-memoria-diversidade-roi"

ROI_MIN = -0.05  # 🔥 nunca trava mais

PREMIOS = {
    11: 6,
    12: 12,
    13: 30,
    14: 1500,
    15: 1500000
}
CUSTO = 3.0

# ======================================================
# AUX
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def linhas(nums):
    ranges = [range(1,6), range(6,11), range(11,16), range(16,21), range(21,26)]
    return [sum(1 for n in nums if n in r) for r in ranges]


def diversidade(j1, j2):
    return len(set(j1) & set(j2))


def estimar_roi(score):
    probs = {
        11: score * 0.6,
        12: score * 0.25,
        13: score * 0.10,
        14: score * 0.04,
        15: score * 0.01
    }
    retorno = sum(probs[k] * PREMIOS[k] for k in probs)
    return (retorno - CUSTO) / CUSTO


# ======================================================
# MEMÓRIA
# ======================================================
def carregar_memoria(supabase):
    res = supabase.table("memoria_cenarios") \
        .select("*") \
        .order("score_medio_real", desc=True) \
        .limit(50) \
        .execute()

    return res.data or []


def escolher_estrutura(memoria):
    if not memoria:
        return None

    top = memoria[:10]
    return random.choice(top)


def gerar_por_estrutura(pool, estrutura):
    if not estrutura:
        return sorted(random.sample(pool, 15))

    pares_target = estrutura["pares"]
    linhas_target = estrutura["linhas"]

    pares = [n for n in pool if n % 2 == 0]
    impares = [n for n in pool if n % 2 != 0]

    escolhidos = []

    escolhidos += random.sample(pares, min(pares_target, len(pares)))
    escolhidos += random.sample(impares, 15 - len(escolhidos))

    return sorted(escolhidos[:15])


# ======================================================
# SCORE
# ======================================================
def score_palpite(nums, scores, fator):
    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores.get(chave, 0)
    return aplicar_fator_aprendizado(base, fator)


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

    memoria = carregar_memoria(supabase)

    if memoria:
        print(f"🧠 Memória carregada: {len(memoria)} cenários")
    else:
        print("⚠️ Sem memória - fallback livre")

    candidatos = []

    # ==================================================
    # GERAÇÃO MASSIVA
    # ==================================================
    for _ in range(MAX_TENTATIVAS):
        estrutura = escolher_estrutura(memoria)
        nums = gerar_por_estrutura(pool, estrutura)

        if len(set(nums)) != 15:
            continue

        score = score_palpite(nums, scores, fator)

        if probs_reais:
            roi = calcular_roi_real(score, probs_reais)
        else:
            roi = estimar_roi(score)

        candidatos.append({
            "nums": nums,
            "score": score,
            "roi": roi
        })

    print(f"📊 {len(candidatos)} candidatos gerados")

    # ==================================================
    # RANKING MULTI-CRITÉRIO
    # ==================================================
    candidatos.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)

    finais = []

    for c in candidatos:
        if len(finais) == 0:
            finais.append(c)
            continue

        # 🔥 diversidade mínima
        if all(diversidade(c["nums"], f["nums"]) <= 10 for f in finais):
            finais.append(c)

        if len(finais) == QTD_FINAL:
            break

    # fallback se não atingir 7
    if len(finais) < QTD_FINAL:
        print("⚠️ Baixa diversidade - completando")
        for c in candidatos:
            if c not in finais:
                finais.append(c)
            if len(finais) == QTD_FINAL:
                break

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | ROI={round(p['roi'],4)} | score={round(p['score'],6)} | {p['nums']}")

    # ==================================================
    # SAVE
    # ==================================================
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

    print("\n✅ Gerador v8 finalizado com inteligência total\n")


if __name__ == "__main__":
    main()
