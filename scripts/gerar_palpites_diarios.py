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
VERSAO = "v7-estrutura-inteligente"
POOL_SIZE = 25

# ======================================================
# BUSCAR MELHORES CENÁRIOS
# ======================================================
def buscar_top_cenarios(supabase, limite=20):
    res = (
        supabase
        .table("memoria_cenarios")
        .select("*")
        .order("score_medio_real", desc=True)
        .limit(limite)
        .execute()
    )

    return res.data or []


# ======================================================
# GERAR PALPITE BASEADO EM ESTRUTURA
# ======================================================
def gerar_por_estrutura(pool, estrutura):
    numeros = []

    linhas_ranges = [
        list(range(1, 6)),
        list(range(6, 11)),
        list(range(11, 16)),
        list(range(16, 21)),
        list(range(21, 26)),
    ]

    for i, qtd in enumerate(estrutura["linhas"]):
        candidatos = list(set(pool) & set(linhas_ranges[i]))
        if len(candidatos) < qtd:
            return None

        numeros += random.sample(candidatos, qtd)

    return sorted(numeros)


# ======================================================
# AJUSTES FINOS (PARES / PRIMOS)
# ======================================================
def ajustar_estrutura(nums, estrutura):
    pares_alvo = estrutura["pares"]
    primos_set = {2,3,5,7,11,13,17,19,23}

    pares = sum(1 for n in nums if n % 2 == 0)

    # ajuste simples
    if pares < pares_alvo:
        nums = sorted(nums, key=lambda x: x % 2)  # prioriza pares
    elif pares > pares_alvo:
        nums = sorted(nums, key=lambda x: -(x % 2))  # prioriza ímpares

    return nums[:15]


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
# DIVERSIFICAÇÃO
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))


def diversificar(lista):
    final = []

    for c in lista:
        if not final:
            final.append(c)
            continue

        if all(distancia(c["nums"], f["nums"]) >= 6 for f in final):
            final.append(c)

        if len(final) >= QTD_FINAL:
            break

    return final


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

    # pool completo (25 números agora)
    pool = list(range(1, 26))

    fator = obter_fator_aprendizado_global()["fator"]
    scores = calcular_score_combinacoes_reais()

    cenarios = buscar_top_cenarios(supabase)

    if not cenarios:
        print("⚠️ Sem memória, fallback padrão")
        return

    candidatos = []

    # ==================================================
    # GERAÇÃO GUIADA POR CENÁRIOS
    # ==================================================
    for cenario in cenarios:
        for _ in range(2000):
            nums = gerar_por_estrutura(pool, cenario)

            if not nums:
                continue

            nums = ajustar_estrutura(nums, cenario)

            score = score_palpite(nums, scores, fator)

            candidatos.append({
                "nums": nums,
                "score": score
            })

    if not candidatos:
        print("❌ Nenhum candidato gerado")
        return

    print(f"📊 {len(candidatos)} candidatos estruturados")

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = diversificar(candidatos)

    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],4)} | {p['nums']}")

    # salvar
    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    registros = []

    for i, p in enumerate(finais, 1):
        pares = sum(1 for n in p["nums"] if n % 2 == 0)
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
                "origem": "memoria_estrutural"
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Geração estrutural concluída\n")


if __name__ == "__main__":
    main()
