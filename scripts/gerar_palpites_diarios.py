import sys
import json
import random
import time
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

# =========================
# CONFIG
# =========================
QTD_FINAL = 7
POOL_SIZE = 22
MAX_TENTATIVAS = 40000
MAX_TEMPO = 15

VERSAO = "v9-auto-adaptativo"

# =========================
# AUX
# =========================
def gerar_pool(supabase):
    return [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(POOL_SIZE)
        .execute().data
    ]


def diversidade(a, b):
    return len(set(a) & set(b))


def valido_basico(nums):
    return len(set(nums)) == 15


def score(nums, scores, fator):
    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )
    return aplicar_fator_aprendizado(scores.get(chave, 0), fator)


# =========================
# MODO ADAPTATIVO
# =========================
def definir_modo(memoria_score):
    if memoria_score > 0.6:
        return "AGRESSIVO"
    elif memoria_score > 0.3:
        return "EQUILIBRADO"
    return "CONSERVADOR"


# =========================
# MAIN
# =========================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    pool = gerar_pool(supabase)

    fator = obter_fator_aprendizado_global()["fator"]
    scores = calcular_score_combinacoes_reais()

    probs = obter_probabilidades_reais(VERSAO)

    # memória média simples
    memoria = supabase.table("memoria_cenarios") \
        .select("score_medio_real") \
        .limit(50).execute().data

    memoria_score = sum(float(m.get("score_medio_real", 0)) for m in memoria) / max(len(memoria),1)

    modo = definir_modo(memoria_score)

    print(f"🧠 Modo ativo: {modo} | memória={round(memoria_score,3)}")

    candidatos = []
    inicio = time.time()

    for _ in range(MAX_TENTATIVAS):

        if time.time() - inicio > MAX_TEMPO:
            print("⚠️ Timeout geração")
            break

        nums = sorted(random.sample(pool, 15))

        if not valido_basico(nums):
            continue

        sc = score(nums, scores, fator)

        if probs and modo == "AGRESSIVO":
            roi = calcular_roi_real(sc, probs)
        else:
            roi = sc * 0.1  # proxy simples

        candidatos.append({
            "nums": nums,
            "score": sc,
            "roi": roi
        })

    if not candidatos:
        print("⚠️ fallback total")
        candidatos = [{
            "nums": sorted(random.sample(pool, 15)),
            "score": 0.1,
            "roi": 0
        } for _ in range(QTD_FINAL)]

    print(f"📊 {len(candidatos)} candidatos")

    # =========================
    # RANKING ADAPTATIVO
    # =========================
    if modo == "AGRESSIVO":
        candidatos.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)
    elif modo == "EQUILIBRADO":
        candidatos.sort(key=lambda x: (x["score"], x["roi"]), reverse=True)
    else:
        candidatos.sort(key=lambda x: x["score"], reverse=True)

    # =========================
    # DIVERSIDADE FORÇADA
    # =========================
    finais = []

    for c in candidatos:
        if all(diversidade(c["nums"], f["nums"]) <= 10 for f in finais):
            finais.append(c)
        if len(finais) == QTD_FINAL:
            break

    # fallback diversidade
    if len(finais) < QTD_FINAL:
        finais = candidatos[:QTD_FINAL]

    # =========================
    # OUTPUT
    # =========================
    print("\n🏆 FINAL:")
    for i, f in enumerate(finais, 1):
        print(f"{i}º | score={round(f['score'],4)} | roi={round(f['roi'],4)} | {f['nums']}")

    # =========================
    # SAVE
    # =========================
    supabase.table("palpites_validos").delete().execute()

    registros = []

    for i, f in enumerate(finais, 1):
        registros.append({
            "data_referencia": hoje,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(f["nums"]),
            "metricas": json.dumps({
                "versao": VERSAO,
                "modo": modo,
                "score": f["score"],
                "roi": f["roi"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ V9 finalizado")


if __name__ == "__main__":
    main()
