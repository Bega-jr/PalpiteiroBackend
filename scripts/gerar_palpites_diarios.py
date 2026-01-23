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
# Configurações
# ======================================================
QTD_ESTATISTICOS = 6
VERSAO_GERADOR = "v3.7-score-real-ranking-safe"
MAX_TENTATIVAS = 15000

SOMA_MIN = 155
SOMA_MAX = 225
PARES_MIN = 5
PARES_MAX = 10
SEQ_MAX = 5
PERCENTIL_MIN = 0.30
REPET_MIN = 7
REPET_MAX = 12
LINHA_MIN = 1
LINHA_MAX = 5

RELAXACOES_SCORE = [1.0, 0.7, 0.5, 0.3, 0.1]

# ======================================================
# Auxiliares
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    impares = 15 - pares
    soma = sum(nums)
    return pares, impares, soma


def max_sequencia(nums):
    atual = seq = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 1
    return seq


def distribuicao_linhas(nums):
    faixas = [
        range(1, 6),
        range(6, 11),
        range(11, 16),
        range(16, 21),
        range(21, 26),
    ]
    return [sum(1 for n in nums if n in f) for f in faixas]


def validar(nums, scores, score_min, ultimos, fator):
    pares, _, soma = calcular_metricas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
    if not (PARES_MIN <= pares <= PARES_MAX):
        return False
    if max_sequencia(nums) > SEQ_MAX:
        return False
    if not all(LINHA_MIN <= x <= LINHA_MAX for x in distribuicao_linhas(nums)):
        return False

    repetidos = len(set(nums) & set(ultimos))
    if not (REPET_MIN <= repetidos <= REPET_MAX):
        return False

    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    score_base = scores.get(chave, 0)
    score_final = aplicar_fator_aprendizado(score_base, fator)

    return score_final >= score_min


def gerar_palpite(pool, scores, score_min, ultimos, fator):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores, score_min, ultimos, fator):
            return nums
    return None


def gerar_palpite_livre(pool):
    return sorted(random.sample(pool, 15))


def calcular_score_palpite(nums, scores, fator):
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
# Main
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

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
        .limit(20).execute().data
    ]

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator aprendizado: {fator}")

    scores = calcular_score_combinacoes_reais()
    valores = sorted(scores.values(), reverse=True)
    score_base = valores[int(len(valores) * PERCENTIL_MIN)]

    print(f"📊 Score base: {score_base}")

    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    palpites = []
    usados = set()

    # ==================================================
    # FIXO COM FALLBACK
    # ==================================================
    fixo = None
    for fator_relax in RELAXACOES_SCORE:
        score_min = score_base * fator_relax
        fixo = gerar_palpite(pool, scores, score_min, ultimos, fator)
        if fixo:
            print(f"🎯 Fixo gerado | score_min={round(score_min,6)}")
            break

    if not fixo:
        print("⚠️ Fixo fallback livre aplicado")
        fixo = gerar_palpite_livre(pool)

    usados.add(tuple(fixo))
    palpites.append(("fixo", fixo))

    # ==================================================
    # ESTATÍSTICOS
    # ==================================================
    while len(palpites) < QTD_ESTATISTICOS + 1:
        p = gerar_palpite(pool, scores, score_base * 0.3, ultimos, fator)
        if not p:
            p = gerar_palpite_livre(pool)

        if tuple(p) not in usados:
            usados.add(tuple(p))
            palpites.append(("estatistico", p))

    # ==================================================
    # RANKING
    # ==================================================
    ranking = []
    for tipo, nums in palpites:
        score = calcular_score_palpite(nums, scores, fator)
        ranking.append({
            "tipo": tipo,
            "numeros": nums,
            "score": score
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)

    print("\n🏆 RANKING FINAL:")
    for i, r in enumerate(ranking, 1):
        print(f"{i}º | score={round(r['score'],6)} | {r['numeros']}")

    # Persistência
    registros = []
    for i, r in enumerate(ranking, 1):
        pares, impares, soma = calcular_metricas(r["numeros"])
        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "tipo": r["tipo"],
            "indice_palpite": i,
            "ranking": i,
            "score_final": r["score"],
            "numeros": json.dumps(r["numeros"]),
            "pares": pares,
            "impares": impares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "aprendizado": "v3-global"
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print("\n✅ Gerador finalizado com segurança total\n")


if __name__ == "__main__":
    main()



