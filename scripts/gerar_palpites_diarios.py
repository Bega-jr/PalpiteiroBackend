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
MAX_TENTATIVAS = 40000
POOL_SIZE = 20
VERSAO = "v9.1-dinamico-diversificado"

# ======================================================
# AUX
# ======================================================
def diversidade_ok(novo, lista):
    for jogo in lista:
        iguais = len(set(novo) & set(jogo))
        if iguais >= 11:
            return False
    return True


def gerar_pool(supabase):
    return [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(POOL_SIZE)
        .execute().data
    ]


def gerar_estrutura():
    return {
        "pares": random.choice([6, 7, 8, 9]),
        "soma_min": 170,
        "soma_max": 220
    }


def gerar_jogo(pool, estrutura):
    tentativas = 0

    while tentativas < 50:
        nums = sorted(random.sample(pool, 15))

        pares = sum(n % 2 == 0 for n in nums)
        soma = sum(nums)

        if pares != estrutura["pares"]:
            tentativas += 1
            continue

        if not (estrutura["soma_min"] <= soma <= estrutura["soma_max"]):
            tentativas += 1
            continue

        return nums

    return None


def score_palpite(nums, scores, fator):
    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores.get(chave, 0)

    score = aplicar_fator_aprendizado(base, fator)

    # 🔥 variação pra evitar empate
    score += random.uniform(-0.05, 0.05)

    return max(score, 0)


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # concurso referência
    concurso_data = supabase.table("lotofacil_concursos") \
        .select("concurso") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    if not concurso_data:
        print("❌ Sem concurso base")
        return

    concurso_ref = concurso_data[0]["concurso"]
    print(f"📌 Concurso referência: {concurso_ref}")

    # pool
    pool = gerar_pool(supabase)

    # aprendizado
    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()

    # ROI
    probs_reais = obter_probabilidades_reais(VERSAO)
    usar_roi_real = probs_reais is not None

    if usar_roi_real:
        print("🧠 ROI real ativo")
    else:
        print("⚠️ ROI fallback ativo")

    # ==================================================
    # GERAR CANDIDATOS
    # ==================================================
    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        estrutura = gerar_estrutura()

        nums = gerar_jogo(pool, estrutura)
        if not nums:
            continue

        score = score_palpite(nums, scores, fator)

        if usar_roi_real:
            roi = calcular_roi_real(score, probs_reais)
        else:
            roi = score * 0.1  # fallback leve

        rank = (score * 0.7) + (roi * 0.3)

        candidatos.append({
            "nums": nums,
            "score": score,
            "roi": roi,
            "rank": rank
        })

    if not candidatos:
        print("❌ Nenhum candidato gerado")
        return

    print(f"📊 {len(candidatos)} candidatos")

    # ==================================================
    # RANKING
    # ==================================================
    candidatos.sort(key=lambda x: x["rank"], reverse=True)

    finais = []

    for c in candidatos:
        if diversidade_ok(c["nums"], [f["nums"] for f in finais]):
            finais.append(c)
        if len(finais) == QTD_FINAL:
            break

    # fallback se não conseguiu diversidade suficiente
    if len(finais) < QTD_FINAL:
        print("⚠️ fallback diversidade")
        finais = candidatos[:QTD_FINAL]

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | roi={round(p['roi'],4)} | {p['nums']}")

    # ==================================================
    # SAVE (SEGURO)
    # ==================================================
    supabase.table("palpites_validos") \
        .delete() \
        .eq("concurso_referencia", concurso_ref) \
        .execute()

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

    print("\n✅ Geração finalizada (v9.1)\n")


if __name__ == "__main__":
    main()
