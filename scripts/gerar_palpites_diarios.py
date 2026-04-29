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

# ======================================================
# CONFIG
# ======================================================
QTD_FINAL = 7
POOL_SIZE = 25
MAX_TENTATIVAS = 20000
VERSAO = "v9.3-fix-sem-duplicacao"

# ======================================================
# DINÂMICO
# ======================================================
def obter_parametros_dinamicos():
    return {
        "soma_min": 160,
        "soma_max": 225,
        "pares_min": 5,
        "pares_max": 10
    }

# ======================================================
# VALIDAÇÃO FORTE
# ======================================================
def validar(nums, params):
    # 🔴 GARANTE unicidade
    if len(set(nums)) != 15:
        return False

    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)

    if not (params["soma_min"] <= soma <= params["soma_max"]):
        return False

    if not (params["pares_min"] <= pares <= params["pares_max"]):
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

    base = scores.get(chave, 0.1)
    return aplicar_fator_aprendizado(base, fator)

# ======================================================
# DIVERSIDADE
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))

def filtrar_diversidade(candidatos):
    finais = []

    for c in candidatos:
        if all(distancia(c["nums"], f["nums"]) >= 5 for f in finais):
            finais.append(c)

        if len(finais) >= QTD_FINAL:
            break

    return finais

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
        .limit(1).execute().data

    if not concurso:
        print("❌ Sem concurso")
        return

    concurso_ref = concurso[0]["concurso"]
    print(f"📌 Concurso referência: {concurso_ref}")

    pool = [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .limit(POOL_SIZE)
        .execute().data
    ]

    params = obter_parametros_dinamicos()
    print(f"📊 Parâmetros: {params}")
    print(f"📊 Pool size: {len(pool)}")

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()

    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        # 🔴 CORREÇÃO CRÍTICA
        nums = sorted(random.sample(pool, 15))

        if not validar(nums, params):
            continue

        score = score_palpite(nums, scores, fator)

        candidatos.append({
            "nums": nums,
            "score": score,
            "roi": score * 0.1
        })

    if not candidatos:
        print("❌ Nenhum candidato gerado")
        return

    print(f"✅ {len(candidatos)} candidatos válidos")

    candidatos.sort(key=lambda x: (x["score"], x["roi"]), reverse=True)

    finais = filtrar_diversidade(candidatos)

    if len(finais) < QTD_FINAL:
        finais = candidatos[:QTD_FINAL]

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | {p['nums']}")

    # ==================================================
    # DELETE SEGURO
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
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(p["nums"]),
            "metricas": json.dumps({
                "versao": VERSAO,
                "score": p["score"],
                "roi": p["roi"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Geração corrigida (sem duplicação)\n")


if __name__ == "__main__":
    main()
