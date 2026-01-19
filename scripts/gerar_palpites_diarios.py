import sys
import json
import random
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v2 import obter_penalidades_por_numero

# -----------------------------------
# Configurações
# -----------------------------------
QTD_ESTATISTICOS = 6
VERSAO_GERADOR = "v2.0-top-historico"
MAX_TENTATIVAS = 7000

SOMA_MIN = 170
SOMA_MAX = 210
PARES_MIN = 6
PARES_MAX = 9
SEQ_MAX = 4

# -----------------------------------
# Métricas
# -----------------------------------
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def max_sequencia(nums):
    seq = atual = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 1
    return seq


def linhas_ok(nums):
    linhas = [
        range(1, 6),
        range(6, 11),
        range(11, 16),
        range(16, 21),
        range(21, 26),
    ]
    return all(any(n in linha for n in nums) for linha in linhas)


def finais_ok(nums):
    finais = {}
    for n in nums:
        f = n % 10
        finais[f] = finais.get(f, 0) + 1
    return max(finais.values()) <= 3


def validar(nums):
    pares, soma = calcular_metricas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
    if not (PARES_MIN <= pares <= PARES_MAX):
        return False
    if max_sequencia(nums) > SEQ_MAX:
        return False
    if not linhas_ok(nums):
        return False
    if not finais_ok(nums):
        return False

    return True

# -----------------------------------
# Geração
# -----------------------------------
def gerar_palpite(pool):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums):
            return nums
    return None

# -----------------------------------
# Execução
# -----------------------------------
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador V2 iniciado — {hoje}")

    estat = (
        supabase.table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    ).data

    if not estat:
        print("❌ Estatísticas diárias não encontradas")
        return

    data_ref = estat[0]["data_referencia"]

    numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, score")
        .eq("data_referencia", data_ref)
        .execute()
    ).data

    if not numeros:
        print("❌ Estatísticas por número não encontradas")
        return

    penalidades = obter_penalidades_por_numero(ano=2026)

    # Score composto
    ranking = []
    for n in numeros:
        fator = penalidades.get(n["numero"], 1.0)
        score_final = n["score"] * fator
        ranking.append({
            "numero": n["numero"],
            "score": score_final
        })

    ranking.sort(key=lambda x: x["score"], reverse=True)

    # Pool mais forte e limpo
    pool = [n["numero"] for n in ranking[:18]]

    supabase.table("palpites_validos") \
        .delete() \
        .eq("data_referencia", data_ref) \
        .execute()

    registros = []
    usados = set()

    # FIXO
    fixo = gerar_palpite(pool)
    usados.add(tuple(fixo))
    pares, soma = calcular_metricas(fixo)

    registros.append({
        "data_referencia": data_ref,
        "tipo": "fixo",
        "indice_palpite": 0,
        "numeros": json.dumps(fixo),
        "pares": pares,
        "soma_total": soma,
        "metricas": json.dumps({
            "versao": VERSAO_GERADOR,
            "origem": "top_historico"
        })
    })

    # ESTATÍSTICOS
    gerados = 0
    while gerados < QTD_ESTATISTICOS:
        palpite = gerar_palpite(pool)
        if not palpite or tuple(palpite) in usados:
            continue

        usados.add(tuple(palpite))
        pares, soma = calcular_metricas(palpite)

        registros.append({
            "data_referencia": data_ref,
            "tipo": "estatistico",
            "indice_palpite": gerados + 1,
            "numeros": json.dumps(palpite),
            "pares": pares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "origem": "estatistico_historico"
            })
        })

        gerados += 1

    supabase.table("palpites_validos").insert(registros).execute()

    print("✅ Palpites gerados com filtro histórico real")
    print("🧠 Aprendizado aplicado")
    print("🎯 V2 finalizada")

if __name__ == "__main__":
    main()
