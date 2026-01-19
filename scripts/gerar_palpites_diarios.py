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
from app.services.estatisticas_combinacao_v2 import (
    calcular_score_combinacoes,
    extrair_metricas_jogo
)

# -----------------------------------
# Configurações
# -----------------------------------
QTD_ESTATISTICOS = 6
VERSAO_GERADOR = "v2.0-score-combinacao"
MAX_TENTATIVAS = 6000

SOMA_MIN = 170
SOMA_MAX = 210
PARES_MIN = 6
PARES_MAX = 9
SEQ_MAX = 4
SCORE_COMBINACAO_MIN = 0.35

# -----------------------------------
# Funções básicas
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

# -----------------------------------
# Validação com SCORE HISTÓRICO
# -----------------------------------
def validar(nums, scores_combinacao):
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

    # 🔥 Score por combinação histórica
    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        m["linhas"]
    )

    score = scores_combinacao.get(chave, 0)

    if score < SCORE_COMBINACAO_MIN:
        return False

    return True

# -----------------------------------
# Geração controlada
# -----------------------------------
def gerar_palpite(pool, scores_combinacao):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores_combinacao):
            return nums
    return None

# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador V2 iniciado para {hoje}")

    # -----------------------------------
    # Estatísticas diárias
    # -----------------------------------
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

    # -----------------------------------
    # Estatísticas por número
    # -----------------------------------
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
    # Penalidades por aprendizado
    # -----------------------------------
    penalidades = obter_penalidades_por_numero(ano=2026)

    numeros_ajustados = []
    for n in numeros:
        fator = penalidades.get(n["numero"], 1.0)
        numeros_ajustados.append({
            "numero": n["numero"],
            "score": n["score"] * fator
        })

    numeros_ajustados.sort(key=lambda x: x["score"], reverse=True)

    # Pool TOP 20
    pool = [n["numero"] for n in numeros_ajustados[:20]]

    # -----------------------------------
    # Score histórico por combinação
    # -----------------------------------
    scores_combinacao = calcular_score_combinacoes()

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
    fixo = gerar_palpite(pool, scores_combinacao)
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
            "origem": "score_combinacao",
            "versao": VERSAO_GERADOR
        })
    })

    # -----------------------------------
    # ESTATÍSTICOS
    # -----------------------------------
    gerados = 0

    while gerados < QTD_ESTATISTICOS:
        palpite = gerar_palpite(pool, scores_combinacao)
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
                "origem": "score_combinacao",
                "versao": VERSAO_GERADOR
            })
        })

        gerados += 1

    # -----------------------------------
    # Persistência
    # -----------------------------------
    supabase.table("palpites_validos").insert(registros).execute()

    print(f"✅ Gerados {1 + gerados} palpites válidos")
    print("🧠 Score histórico aplicado")
    print("🎯 Gerador V2 finalizado")

if __name__ == "__main__":
    main()
