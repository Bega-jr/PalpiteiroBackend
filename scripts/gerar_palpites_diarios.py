import sys
import json
import random
from pathlib import Path
from datetime import datetime

# ======================================================
# SETUP
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
from app.services.roi_service import (
    obter_probabilidades_reais,
    calcular_roi_real
)

# ======================================================
# CONFIG
# ======================================================
VERSAO = "v8.1-memoria-diversidade-roi"
QTD_FINAL = 7
POOL_SIZE = 23
MAX_TENTATIVAS = 40000

ROI_MIN = 0.01
DIVERSIDADE_MIN = 8  # diferença mínima entre jogos

# fallback ROI
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
def diversidade(jogo1, jogo2):
    return len(set(jogo1) ^ set(jogo2))


def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


# ======================================================
# GERAÇÃO SEGURA (CORRIGIDA)
# ======================================================
def gerar_por_estrutura(pool, estrutura):
    pares = [n for n in pool if n % 2 == 0]
    impares = [n for n in pool if n % 2 != 0]

    alvo_pares = estrutura["pares"]
    alvo_impares = 15 - alvo_pares

    escolhidos = []

    qtd_pares = min(alvo_pares, len(pares))
    qtd_impares = min(alvo_impares, len(impares))

    escolhidos += random.sample(pares, qtd_pares)
    escolhidos += random.sample(impares, qtd_impares)

    # completar até 15
    while len(escolhidos) < 15:
        n = random.choice(pool)
        if n not in escolhidos:
            escolhidos.append(n)

    return sorted(escolhidos)


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
def estimar_roi(score):
    probs = {
        11: score * 0.6,
        12: score * 0.25,
        13: score * 0.1,
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

    # pool expandido
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
    usar_roi_real = bool(probs_reais)

    memoria = carregar_memoria(supabase)
    print(f"🧠 Memória carregada: {len(memoria)} cenários")

    candidatos = []

    # ==================================================
    # GERAÇÃO BASEADA EM MEMÓRIA
    # ==================================================
    for _ in range(MAX_TENTATIVAS):

        if memoria:
            estrutura = random.choice(memoria)
        else:
            estrutura = {
                "pares": random.randint(6, 9)
            }

        nums = gerar_por_estrutura(pool, estrutura)

        score = score_palpite(nums, scores, fator)

        if usar_roi_real:
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
        if len(finais) >= QTD_FINAL:
            break

        if all(diversidade(c["nums"], f["nums"]) >= DIVERSIDADE_MIN for f in finais):
            finais.append(c)

    # fallback
    if len(finais) < QTD_FINAL:
        for c in candidatos:
            if len(finais) >= QTD_FINAL:
                break
            finais.append(c)

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

    print("\n✅ Geração concluída (memória + diversidade + ROI)\n")


if __name__ == "__main__":
    main()
