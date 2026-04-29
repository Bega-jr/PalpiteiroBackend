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
VERSAO = "v6-diversificado-roi"

ROI_MIN = -0.05  # mais flexível

# fallback
PREMIOS_FIXOS = {
    11: 6,
    12: 12,
    13: 30,
    14: 1500,
    15: 1500000
}

CUSTO_JOGO = 3.0

# ======================================================
# AUX
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def max_seq(nums):
    seq = atual = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 1
    return seq


def linhas(nums):
    ranges = [range(1,6), range(6,11), range(11,16), range(16,21), range(21,26)]
    return [sum(1 for n in nums if n in r) for r in ranges]


def validar(nums, soma_media, pares_media):
    if len(set(nums)) != 15:
        return False

    pares, soma = calcular_metricas(nums)

    # 🔥 limites dinâmicos
    if not (soma_media - 25 <= soma <= soma_media + 25):
        return False

    if not (pares_media - 3 <= pares <= pares_media + 3):
        return False

    if max_seq(nums) > 6:
        return False

    if not all(1 <= x <= 5 for x in linhas(nums)):
        return False

    return True


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
# ROI
# ======================================================
def estimar_roi_fallback(score):
    probs = {
        11: score * 0.6,
        12: score * 0.25,
        13: score * 0.10,
        14: score * 0.04,
        15: score * 0.01
    }

    retorno = sum(probs[k] * PREMIOS_FIXOS[k] for k in probs)
    roi = (retorno - CUSTO_JOGO) / CUSTO_JOGO

    return round(roi, 4)


# ======================================================
# DIVERSIDADE
# ======================================================
def intersecao(a, b):
    return len(set(a) & set(b))


def selecionar_diversificados(candidatos, qtd=7, max_inter=8):
    selecionados = []

    for c in candidatos:
        nums = c["nums"]

        if not selecionados:
            selecionados.append(c)
            continue

        valido = True

        for s in selecionados:
            if intersecao(nums, s["nums"]) > max_inter:
                valido = False
                break

        if valido:
            selecionados.append(c)

        if len(selecionados) == qtd:
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
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1).execute().data[0]

    concurso_ref = concurso["concurso"]

    # médias dinâmicas
    stats = supabase.table("estatisticas_diarias_v2") \
        .select("media_soma, media_pares") \
        .order("data_referencia", desc=True) \
        .limit(1).execute().data

    soma_media = stats[0]["media_soma"] if stats else 195
    pares_media = stats[0]["media_pares"] if stats else 8

    # pool
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

    if probs_reais:
        print("🧠 ROI real ativo")
    else:
        print("⚠️ ROI fallback ativo")

    # ==================================================
    # GERAR
    # ==================================================
    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))

        if not validar(nums, soma_media, pares_media):
            continue

        score = score_palpite(nums, scores, fator)

        if probs_reais:
            roi = calcular_roi_real(score, probs_reais)
        else:
            roi = estimar_roi_fallback(score)

        candidatos.append({
            "nums": nums,
            "score": score,
            "roi": roi
        })

    if not candidatos:
        print("❌ Nenhum candidato válido")
        return

    print(f"📊 {len(candidatos)} candidatos gerados")

    # ==================================================
    # RANKING + DIVERSIDADE
    # ==================================================
    candidatos.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)

    filtrados = [c for c in candidatos if c["roi"] >= ROI_MIN]

    base = filtrados if len(filtrados) >= QTD_FINAL else candidatos

    finais = selecionar_diversificados(base, QTD_FINAL)

    if len(finais) < QTD_FINAL:
        print("⚠️ Complementando por score")
        for c in base:
            if c not in finais:
                finais.append(c)
            if len(finais) == QTD_FINAL:
                break

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 RANKING FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | ROI={p['roi']} | score={round(p['score'],6)} | {p['nums']}")

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

    print("\n✅ Gerador finalizado com diversidade + ROI\n")


if __name__ == "__main__":
    main()
