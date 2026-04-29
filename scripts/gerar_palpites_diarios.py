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
# POOL SEM DUPLICAÇÃO
# =========================
def gerar_pool(supabase):
    data = supabase.table("estatisticas_numeros") \
        .select("numero") \
        .order("score", desc=True) \
        .limit(50) \
        .execute().data

    numeros = list({int(r["numero"]) for r in data})

    if len(numeros) < 15:
        numeros = list(range(1, 26))

    return numeros[:POOL_SIZE]

# =========================
# AUX
# =========================
def diversidade(a, b):
    return len(set(a) & set(b))


def score(nums, scores, fator):
    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )
    return aplicar_fator_aprendizado(scores.get(chave, 0), fator)


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

        sc = score(nums, scores, fator)

        if probs and modo == "AGRESSIVO":
            roi = calcular_roi_real(sc, probs)
        else:
            roi = sc * 0.1

        candidatos.append({
            "nums": nums,
            "score": sc,
            "roi": roi
        })

    # =========================
    # FALLBACK REAL
    # =========================
    if not candidatos:
        print("⚠️ fallback total")

        candidatos = []
        for _ in range(QTD_FINAL):
            nums = sorted(random.sample(range(1, 26), 15))
            candidatos.append({
                "nums": nums,
                "score": 0.1,
                "roi": 0
            })

    print(f"📊 {len(candidatos)} candidatos")

    # =========================
    # RANKING
    # =========================
    if modo == "AGRESSIVO":
        candidatos.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)
    elif modo == "EQUILIBRADO":
        candidatos.sort(key=lambda x: (x["score"], x["roi"]), reverse=True)
    else:
        candidatos.sort(key=lambda x: x["score"], reverse=True)

    # =========================
    # DIVERSIDADE
    # =========================
    finais = []

    for c in candidatos:
        if all(diversidade(c["nums"], f["nums"]) <= 10 for f in finais):
            finais.append(c)
        if len(finais) == QTD_FINAL:
            break

    if len(finais) < QTD_FINAL:
        finais = candidatos[:QTD_FINAL]

    # =========================
    # OUTPUT
    # =========================
    print("\n🏆 FINAL:")
    for i, f in enumerate(finais, 1):
        print(f"{i}º | score={round(f['score'],4)} | roi={round(f['roi'],4)} | {f['nums']}")

    # =========================
    # DELETE SEGURO
    # =========================
    supabase.table("palpites_validos") \
        .delete() \
        .eq("data_referencia", hoje) \
        .execute()

    # =========================
    # SAVE
    # =========================
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

    print("\n✅ V9 finalizado com sucesso")


if __name__ == "__main__":
    main()
