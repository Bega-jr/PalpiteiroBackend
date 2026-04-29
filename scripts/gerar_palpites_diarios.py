import sys
import json
import random
from pathlib import Path
from datetime import datetime
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.estatisticas_service import carregar_historico
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global

# ======================================================
# CONFIG
# ======================================================
QTD_FINAL = 7
POOL_SIZE = 22
MAX_TENTATIVAS = 20000
VERSAO = "v9.2-dinamico-flex"

CUSTO_JOGO = 3.0

# ======================================================
# DINÂMICO BASEADO NO HISTÓRICO
# ======================================================
def calcular_parametros_dinamicos(historico):
    ultimos = historico[-200:]

    somas = [sum(h["numeros"]) for h in ultimos]
    pares = [sum(1 for n in h["numeros"] if n % 2 == 0) for h in ultimos]

    return {
        "soma_min": int(np.percentile(somas, 5)),
        "soma_max": int(np.percentile(somas, 95)),
        "pares_min": int(np.percentile(pares, 5)),
        "pares_max": int(np.percentile(pares, 95)),
    }

# ======================================================
# VALIDAÇÃO FLEXÍVEL (COM RELAXAMENTO)
# ======================================================
def validar(nums, params, relax=0):
    nums = sorted(nums)

    if len(set(nums)) != 15:
        return False

    soma = sum(nums)
    pares = sum(1 for n in nums if n % 2 == 0)

    if not (params["soma_min"] - relax <= soma <= params["soma_max"] + relax):
        return False

    if not (params["pares_min"] - relax <= pares <= params["pares_max"] + relax):
        return False

    return True

# ======================================================
# SCORE SIMPLES (ROBUSTO)
# ======================================================
def score_palpite(nums, freq_map, fator):
    base = sum(freq_map.get(n, 0) for n in nums) / 15
    return base * fator

# ======================================================
# ROI (SECUNDÁRIO)
# ======================================================
def calcular_roi(score):
    retorno = score * 100  # aproximação simples
    return (retorno - CUSTO_JOGO) / CUSTO_JOGO

# ======================================================
# DIVERSIDADE
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))

def diversificar(lista, qtd):
    finais = []

    for cand in lista:
        if len(finais) == 0:
            finais.append(cand)
            continue

        if all(distancia(cand["nums"], f["nums"]) >= 5 for f in finais):
            finais.append(cand)

        if len(finais) == qtd:
            break

    return finais

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    # ==================================================
    # CONCURSO REFERÊNCIA
    # ==================================================
    concursos = supabase.table("lotofacil_concursos") \
        .select("concurso") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    if not concursos:
        print("❌ Sem concurso base")
        return

    concurso_ref = concursos[0]["concurso"]
    print(f"📌 Concurso referência: {concurso_ref}")

    # ==================================================
    # HISTÓRICO + PARÂMETROS
    # ==================================================
    historico = carregar_historico()
    params = calcular_parametros_dinamicos(historico)

    print(f"📊 Parâmetros dinâmicos: {params}")

    # ==================================================
    # POOL
    # ==================================================
    dados = supabase.table("estatisticas_numeros") \
        .select("numero, frequencia") \
        .order("score", desc=True) \
        .limit(POOL_SIZE).execute().data

    pool = [r["numero"] for r in dados]
    freq_map = {r["numero"]: r["frequencia"] for r in dados}

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    # ==================================================
    # GERAÇÃO COM RELAXAMENTO PROGRESSIVO
    # ==================================================
    candidatos = []

    for relax in [0, 2, 5, 10]:
        print(f"🔄 Tentando com relaxamento: {relax}")

        for _ in range(MAX_TENTATIVAS):
            nums = sorted(random.sample(pool, 15))

            if not validar(nums, params, relax):
                continue

            score = score_palpite(nums, freq_map, fator)
            roi = calcular_roi(score)

            candidatos.append({
                "nums": nums,
                "score": score,
                "roi": roi
            })

        if candidatos:
            print(f"✅ {len(candidatos)} candidatos encontrados")
            break

    if not candidatos:
        print("❌ Nenhum candidato gerado (nem com relaxamento)")
        return

    # ==================================================
    # RANKING MULTICRITÉRIO
    # ==================================================
    candidatos.sort(key=lambda x: (x["score"], x["roi"]), reverse=True)

    # diversidade
    finais = diversificar(candidatos, QTD_FINAL)

    if len(finais) < QTD_FINAL:
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
        pares = sum(1 for n in p["nums"] if n % 2 == 0)

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(p["nums"]),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": sum(p["nums"]),
            "metricas": json.dumps({
                "versao": VERSAO,
                "score": p["score"],
                "roi": p["roi"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Geração concluída com sucesso\n")


if __name__ == "__main__":
    main()
