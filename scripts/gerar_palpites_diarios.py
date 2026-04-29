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
POOL_SIZE = 20
MAX_TENTATIVAS = 40000
VERSAO = "v8-estrutura-memoria-diversificada"

DIVERSIDADE_MINIMA = 6

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


def validar(nums):
    if len(set(nums)) != 15:
        return False

    pares, soma = calcular_metricas(nums)

    if not (155 <= soma <= 225):
        return False

    if not (5 <= pares <= 10):
        return False

    if max_seq(nums) > 6:
        return False

    if not all(1 <= x <= 5 for x in linhas(nums)):
        return False

    return True

# ======================================================
# MEMÓRIA
# ======================================================
def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": tuple(linhas(nums))
    }


def buscar_memoria(supabase):
    res = supabase.table("memoria_cenarios") \
        .select("*") \
        .order("score_medio_real", desc=True) \
        .limit(30) \
        .execute()

    return res.data or []


def score_memoria(estrutura, memorias):
    for m in memorias:
        if (
            m["soma_faixa"] == estrutura["soma_faixa"] and
            m["pares"] == estrutura["pares"] and
            m["primos"] == estrutura["primos"]
        ):
            return float(m.get("score_medio_real", 0))

    return 0

# ======================================================
# SCORE MULTI-CRITÉRIO
# ======================================================
def score_palpite(nums, scores, fator, memorias, ultimos):
    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    base = scores.get(chave, 0)
    base = aplicar_fator_aprendizado(base, fator)

    estrutura = extrair_estrutura(nums)
    memoria = score_memoria(estrutura, memorias)

    repeticao = len(set(nums) & set(ultimos))
    sequencia = max_seq(nums)

    diversidade = len(set(nums))

    return {
        "score": base,
        "memoria": memoria,
        "repeticao": repeticao,
        "sequencia": sequencia,
        "diversidade": diversidade
    }

# ======================================================
# DISTÂNCIA ENTRE JOGOS
# ======================================================
def distancia(a, b):
    return len(set(a) ^ set(b))

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
    ultimos = list(map(int, concurso["dezenas"]))

    pool = [
        r["numero"]
        for r in supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(POOL_SIZE)
        .execute().data
    ]

    fator = obter_fator_aprendizado_global()["fator"]
    scores = calcular_score_combinacoes_reais()
    memorias = buscar_memoria(supabase)

    print(f"🧠 Memórias carregadas: {len(memorias)}")

    candidatos = []

    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))

        if not validar(nums):
            continue

        sc = score_palpite(nums, scores, fator, memorias, ultimos)

        candidatos.append({
            "nums": nums,
            **sc
        })

    print(f"📊 {len(candidatos)} candidatos gerados")

    if not candidatos:
        print("❌ Nenhum candidato válido")
        return

    # ==================================================
    # RANKING MULTI-CRITÉRIO
    # ==================================================
    candidatos.sort(
        key=lambda x: (
            x["score"],
            x["memoria"],
            -x["repeticao"],
            -x["sequencia"],
            x["diversidade"]
        ),
        reverse=True
    )

    # ==================================================
    # DIVERSIDADE FORÇADA
    # ==================================================
    finais = []

    for c in candidatos:
        if len(finais) == 0:
            finais.append(c)
            continue

        if all(distancia(c["nums"], f["nums"]) >= DIVERSIDADE_MINIMA for f in finais):
            finais.append(c)

        if len(finais) == QTD_FINAL:
            break

    # fallback
    if len(finais) < QTD_FINAL:
        print("⚠️ Fallback diversidade")
        finais = candidatos[:QTD_FINAL]

    # ==================================================
    # OUTPUT
    # ==================================================
    print("\n🏆 FINAL:")
    for i, p in enumerate(finais, 1):
        print(f"{i}º | score={round(p['score'],6)} | mem={p['memoria']} | {p['nums']}")

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
                "memoria": p["memoria"]
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Gerador v8 finalizado com inteligência total\n")


if __name__ == "__main__":
    main()
