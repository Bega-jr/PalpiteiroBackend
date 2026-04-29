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
VERSAO = "v9-auto-adaptativo"

ROI_MIN = 0.01
CUSTO_JOGO = 3.0

# ======================================================
# AUX
# ======================================================
def validar(nums):
    # evita bug de números repetidos
    if len(nums) != 15 or len(set(nums)) != 15:
        return False

    nums = sorted(nums)

    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)

    if not (150 <= soma <= 230):
        return False

    if not (5 <= pares <= 10):
        return False

    return True


def diversidade_ok(novo, existentes, min_diff=5):
    for e in existentes:
        intersec = len(set(novo) & set(e))
        if intersec > (15 - min_diff):
            return False
    return True


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
    return round(score * 0.1, 4)


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # ==================================================
    # CONCURSO REFERÊNCIA (COM FALLBACK)
    # ==================================================
    concurso_data = supabase.table("lotofacil_concursos") \
        .select("concurso") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    if not concurso_data:
        print("❌ Nenhum concurso encontrado")
        return

    concurso_ref = concurso_data[0]["concurso"]

    if not concurso_ref:
        print("❌ concurso_referencia inválido")
        return

    print(f"📌 Concurso referência: {concurso_ref}")

    # ==================================================
    # POOL
    # ==================================================
    pool = [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(POOL_SIZE)
        .execute().data
    ]

    if len(pool) < 15:
        print("❌ Pool insuficiente")
        return

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()

    probs_reais = obter_probabilidades_reais(VERSAO)

    if probs_reais:
        print("🧠 ROI real ativo")
    else:
        print("⚠️ ROI fallback ativo")

    # ==================================================
    # GERAR CANDIDATOS
    # ==================================================
    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))

        if not validar(nums):
            continue

        score = score_palpite(nums, scores, fator)

        roi = calcular_roi_real(score, probs_reais) if probs_reais else estimar_roi(score)

        candidatos.append({
            "nums": nums,
            "score": score,
            "roi": roi
        })

    if not candidatos:
        print("❌ Nenhum candidato válido")
        return

    print(f"📊 {len(candidatos)} candidatos")

    # ==================================================
    # RANKING
    # ==================================================
    candidatos.sort(key=lambda x: (x["roi"], x["score"]), reverse=True)

    finais = []

    for c in candidatos:
        if len(finais) >= QTD_FINAL:
            break

        if diversidade_ok(c["nums"], [f["nums"] for f in finais]):
            finais.append(c)

    if len(finais) < QTD_FINAL:
        print("⚠️ Diversidade insuficiente, completando...")
        for c in candidatos:
            if len(finais) >= QTD_FINAL:
                break
            finais.append(c)

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | roi={p['roi']} | {p['nums']}")

    # ==================================================
    # DELETE SEGURO (OBRIGATÓRIO WHERE)
    # ==================================================
    supabase.table("palpites_validos") \
        .delete() \
        .eq("concurso_referencia", concurso_ref) \
        .execute()

    # ==================================================
    # SAVE
    # ==================================================
    registros = []

    for i, p in enumerate(finais, 1):
        pares = sum(n % 2 == 0 for n in p["nums"])
        soma = sum(p["nums"])

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

    print("\n✅ Palpites salvos com sucesso\n")


if __name__ == "__main__":
    main()
