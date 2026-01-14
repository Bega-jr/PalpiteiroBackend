import sys
import json
import random
from pathlib import Path
from datetime import datetime

# -----------------------------------
# Setup base
# -----------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service import obter_penalidades_por_numero

# -----------------------------------
# Configurações
# -----------------------------------
QTD_ESTATISTICOS = 6
VERSAO_GERADOR = "v1.2-top-auto"
MAX_TENTATIVAS = 5000

SOMA_MIN = 170
SOMA_MAX = 210
PARES_MIN = 6
PARES_MAX = 9
SEQ_MAX = 4

# -----------------------------------
# Funções de validação
# -----------------------------------
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
    pares, _, soma = calcular_metricas(nums)

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
# Geração controlada
# -----------------------------------
def gerar_palpite(pool):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums):
            return nums
    return None

# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador TOP v1.2 iniciado para {hoje}")

    # Estatística diária
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

    # Estatísticas por número
    numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, score")
        .eq("data_referencia", data_ref)
        .execute()
    ).data

    if not numeros:
        print("❌ Estatísticas por número não encontradas")
        return

    # -----------------------------------
    # Auto-aprendizado (penalidades)
    # -----------------------------------
    penalidades = obter_penalidades_por_numero(ano=2026)

    numeros_ajustados = []
    for n in numeros:
        fator = penalidades.get(n["numero"], 1.0)
        score_ajustado = n["score"] * fator
        numeros_ajustados.append({
            "numero": n["numero"],
            "score": score_ajustado
        })

    numeros_ajustados.sort(key=lambda x: x["score"], reverse=True)

    # Pool TOP 20 ajustado por aprendizado
    pool = [n["numero"] for n in numeros_ajustados[:20]]

    # -----------------------------------
    # Limpa palpites do dia
    # -----------------------------------
    supabase.table("palpites_validos") \
        .delete() \
        .eq("data_referencia", data_ref) \
        .execute()

    registros = []
    usados = set()

    # -----------------------------------
    # FIXO
    # -----------------------------------
    fixo = gerar_palpite(pool)
    if not fixo:
        print("❌ Falha ao gerar palpite fixo")
        return

    usados.add(tuple(fixo))
    pares, impares, soma = calcular_metricas(fixo)

    registros.append({
        "data_referencia": data_ref,
        "tipo": "fixo",
        "indice_palpite": 0,
        "numeros": json.dumps(fixo),
        "pares": pares,
        "impares": impares,
        "soma_total": soma,
        "metricas": json.dumps({
            "origem": "top_score_auto",
            "versao": VERSAO_GERADOR
        })
    })

    # -----------------------------------
    # ESTATÍSTICOS
    # -----------------------------------
    gerados = 0

    while gerados < QTD_ESTATISTICOS:
        palpite = gerar_palpite(pool)
        if not palpite:
            break

        if tuple(palpite) in usados:
            continue

        usados.add(tuple(palpite))
        pares, impares, soma = calcular_metricas(palpite)

        registros.append({
            "data_referencia": data_ref,
            "tipo": "estatistico",
            "indice_palpite": gerados + 1,
            "numeros": json.dumps(palpite),
            "pares": pares,
            "impares": impares,
            "soma_total": soma,
            "metricas": json.dumps({
                "origem": "estatistico_auto",
                "versao": VERSAO_GERADOR
            })
        })

        gerados += 1

    # -----------------------------------
    # Persistência
    # -----------------------------------
    supabase.table("palpites_validos").insert(registros).execute()

    print(f"✅ Gerados {1 + gerados} palpites válidos")
    print("🧠 Auto-aprendizado aplicado")
    print("🎯 Gerador TOP finalizado")

if __name__ == "__main__":
    main()
