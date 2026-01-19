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
from app.services.aprendizado_service_v2 import obter_penalidades_por_numero
from app.services.estatisticas_combinacao_v2 import (
    calcular_score_combinacoes,
    extrair_metricas_jogo
)

# -----------------------------------
# Configurações
# -----------------------------------
QTD_ESTATISTICOS = 6
VERSAO_GERADOR = "v2.1-consistencia-historica"
MAX_TENTATIVAS = 7000

SOMA_MIN = 170
SOMA_MAX = 210

PARES_MIN = 6
PARES_MAX = 9

SEQ_MAX = 4

# Score histórico (percentil)
PERCENTIL_MIN = 0.60  # aceita apenas top 40% histórico

# Repetição com concursos recentes
REPET_MIN = 8
REPET_MAX = 11

# Distribuição espacial por linha (1–5, 6–10, etc)
LINHA_MIN = 2
LINHA_MAX = 4

# -----------------------------------
# Funções auxiliares
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

def distribuicao_linhas(nums):
    linhas = {
        1: range(1, 6),
        2: range(6, 11),
        3: range(11, 16),
        4: range(16, 21),
        5: range(21, 26),
    }
    contagem = []
    for r in linhas.values():
        contagem.append(sum(1 for n in nums if n in r))
    return contagem

def linhas_ok(nums):
    dist = distribuicao_linhas(nums)
    return all(LINHA_MIN <= x <= LINHA_MAX for x in dist)

def finais_ok(nums):
    finais = {}
    for n in nums:
        f = n % 10
        finais[f] = finais.get(f, 0) + 1
    return max(finais.values()) <= 3

def repeticao_ok(nums, ultimos):
    repetidos = len(set(nums) & set(ultimos))
    return REPET_MIN <= repetidos <= REPET_MAX

# -----------------------------------
# Validação principal
# -----------------------------------
def validar(nums, scores_combinacao, score_min, ultimos):
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
    if not repeticao_ok(nums, ultimos):
        return False

    # Score histórico por combinação
    m = extrair_metricas_jogo(nums)
    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        m["linhas"]
    )

    score = scores_combinacao.get(chave, 0)
    return score >= score_min

# -----------------------------------
# Geração controlada
# -----------------------------------
def gerar_palpite(pool, scores_combinacao, score_min, ultimos):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores_combinacao, score_min, ultimos):
            return nums
    return None

# -----------------------------------
# Execução principal
# -----------------------------------
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador V2.1 iniciado para {hoje}")

    # -----------------------------------
    # Último concurso (repetição)
    # -----------------------------------
    ultimo = (
        supabase.table("lotofacil_concursos")
        .select("dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    ).data

    ultimos_numeros = [int(n) for n in ultimo[0]["dezenas"]]

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

    numeros_ajustados = [
        {
            "numero": n["numero"],
            "score": n["score"] * penalidades.get(n["numero"], 1.0)
        }
        for n in numeros
    ]

    numeros_ajustados.sort(key=lambda x: x["score"], reverse=True)

    pool = [n["numero"] for n in numeros_ajustados[:20]]

    # -----------------------------------
    # Score histórico por combinação
    # -----------------------------------
    scores_combinacao = calcular_score_combinacoes()
    scores_validos = sorted(scores_combinacao.values(), reverse=True)

    idx = int(len(scores_validos) * PERCENTIL_MIN)
    score_min = scores_validos[idx]

    print(f"📊 Score mínimo por percentil: {score_min}")

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
    fixo = gerar_palpite(pool, scores_combinacao, score_min, ultimos_numeros)
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
            "origem": "consistencia_historica",
            "versao": VERSAO_GERADOR
        })
    })

    # -----------------------------------
    # ESTATÍSTICOS
    # -----------------------------------
    gerados = 0

    while gerados < QTD_ESTATISTICOS:
        palpite = gerar_palpite(pool, scores_combinacao, score_min, ultimos_numeros)
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
                "origem": "consistencia_historica",
                "versao": VERSAO_GERADOR
            })
        })

        gerados += 1

    # -----------------------------------
    # Persistência
    # -----------------------------------
    supabase.table("palpites_validos").insert(registros).execute()

    print(f"✅ Gerados {1 + gerados} palpites válidos")
    print("📈 Consistência histórica aplicada")
    print("🎯 Gerador V2.1 finalizado")

if __name__ == "__main__":
    main()
