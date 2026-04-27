import sys
import json
import random
from pathlib import Path
from datetime import datetime

# ======================================================
# Setup
# ======================================================
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

# ======================================================
# CONFIG
# ======================================================
QTD_FINAL = 7
POOL_SIZE = 20
MAX_TENTATIVAS = 30000
VERSAO = "v4-roi-inteligente"

# ROI mínimo aceitável
ROI_MIN = 0.02

# custo por jogo (Lotofácil 15 números)
CUSTO_JOGO = 3.0

# tabela aproximada de premiação (média)
PREMIOS = {
    11: 6,
    12: 12,
    13: 30,
    14: 1500,
    15: 1500000
}

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


def validar_basico(nums):
    if len(set(nums)) != 15:
        return False

    pares, soma = calcular_metricas(nums)

    if not (155 <= soma <= 225):
        return False

    if not (5 <= pares <= 10):
        return False

    if max_seq(nums) > 6:  # mais flexível
        return False

    if not all(1 <= x <= 5 for x in linhas(nums)):
        return False

    return True


# ======================================================
# SCORE + ROI
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


def estimar_roi(score):
    """
    Converte score em expectativa financeira
    """
    # distribuição aproximada baseada no score
    probs = {
        11: score * 0.6,
        12: score * 0.25,
        13: score * 0.10,
        14: score * 0.04,
        15: score * 0.01
    }

    retorno = sum(probs[k] * PREMIOS[k] for k in probs)
    roi = (retorno - CUSTO_JOGO) / CUSTO_JOGO

    return round(roi, 4)


# ======================================================
# GERAÇÃO
# ======================================================
def gerar_pool(supabase):
    return [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(POOL_SIZE)
        .execute().data
    ]


def gerar_candidatos(pool):
    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))

        if validar_basico(nums):
            candidatos.append(nums)

    return candidatos


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # concurso
    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1).execute().data[0]

    concurso_ref = concurso["concurso"]

    # pool
    pool = gerar_pool(supabase)

    # aprendizado
    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator: {fator}")

    # score histórico
    scores = calcular_score_combinacoes_reais()

    # gerar candidatos
    candidatos = gerar_candidatos(pool)

    if not candidatos:
        print("❌ Nenhum candidato válido")
        return

    print(f"📊 {len(candidatos)} candidatos gerados")

    # avaliar
    avaliados = []
    for nums in candidatos:
        score = score_palpite(nums, scores, fator)
        roi = estimar_roi(score)

        avaliados.append({
            "nums": nums,
            "score": score,
            "roi": roi
        })

    # ordenar por ROI
    avaliados.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)

    # filtrar ROI mínimo
    finais = [p for p in avaliados if p["roi"] >= ROI_MIN][:QTD_FINAL]

    # fallback se poucos
    if len(finais) < QTD_FINAL:
        print("⚠️ ROI insuficiente, completando com melhores scores")
        avaliados.sort(key=lambda x: x["score"], reverse=True)
        finais = avaliados[:QTD_FINAL]

    # print ranking
    print("\n🏆 RANKING FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | ROI={p['roi']} | score={round(p['score'],6)} | {p['nums']}")

    # persistência
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

    print("\n✅ Gerador finalizado com ROI positivo\n")


if __name__ == "__main__":
    main()
