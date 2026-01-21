import sys
import json
import random
from pathlib import Path
from datetime import datetime

# ======================================================
# Setup base
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
VERSAO_GERADOR = "v3-score-real-historico"
MAX_TENTATIVAS = 9000

SOMA_MIN = 170
SOMA_MAX = 210

PARES_MIN = 6
PARES_MAX = 9

SEQ_MAX = 4

PERCENTIL_MIN = 0.65
REPET_MIN = 8
REPET_MAX = 11

LINHA_MIN = 2
LINHA_MAX = 4

# ======================================================
# Funções auxiliares
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
    linhas = [
        range(1, 6),
        range(6, 11),
        range(11, 16),
        range(16, 21),
        range(21, 26),
    ]
    return [sum(1 for n in nums if n in r) for r in linhas]


def linhas_ok(nums):
    return all(LINHA_MIN <= x <= LINHA_MAX for x in distribuicao_linhas(nums))


def finais_ok(nums):
    finais = {}
    for n in nums:
        f = n % 10
        finais[f] = finais.get(f, 0) + 1
    return max(finais.values()) <= 3


def repeticao_ok(nums, ultimos):
    repetidos = len(set(nums) & set(ultimos))
    return REPET_MIN <= repetidos <= REPET_MAX


# ======================================================
# Validação principal
# ======================================================
def validar(nums, scores_combinacao, score_min, ultimos, fator_aprendizado):
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

    m = extrair_metricas_jogo(nums)

    chave = (
        round(m["soma"] / 10) * 10,
        m["pares"],
        m["primos"],
        tuple(m["linhas"])
    )

    score_base = scores_combinacao.get(chave, 0)
    score_final = aplicar_fator_aprendizado(score_base, fator_aprendizado)

    return score_final >= score_min


# ======================================================
# Geração controlada
# ======================================================
def gerar_palpite(pool, scores_combinacao, score_min, ultimos, fator_aprendizado):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores_combinacao, score_min, ultimos, fator_aprendizado):
            return nums
    return None


# ======================================================
# Execução principal
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    # --------------------------------------------------
    # Concurso oficial
    # --------------------------------------------------
    ultimo_concurso = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    ).data

    concurso_ref = ultimo_concurso[0]["concurso"]
    ultimos_numeros = list(map(int, ultimo_concurso[0]["dezenas"]))

    # --------------------------------------------------
    # Estatísticas por número (SOMENTE PARA POOL)
    # --------------------------------------------------
    estat_numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, score")
        .order("score", desc=True)
        .execute()
    ).data

    if not estat_numeros:
        print("❌ Estatísticas de números não encontradas")
        return

    pool = [n["numero"] for n in estat_numeros[:20]]

    # --------------------------------------------------
    # Aprendizado V3 (GLOBAL)
    # --------------------------------------------------
    aprendizado = obter_fator_aprendizado_global()
    fator_aprendizado = aprendizado["fator"]

    print(f"🧠 Fator de aprendizado global: {fator_aprendizado}")

    # --------------------------------------------------
    # Score real por combinação histórica
    # --------------------------------------------------
    scores_combinacao = calcular_score_combinacoes_reais()
    valores = sorted(scores_combinacao.values(), reverse=True)

    corte = int(len(valores) * PERCENTIL_MIN)
    score_min = valores[corte]

    print(f"📊 Score mínimo real aplicado: {score_min}")

    # --------------------------------------------------
    # Limpeza do concurso
    # --------------------------------------------------
    supabase.table("palpites_validos") \
        .delete() \
        .eq("concurso_referencia", concurso_ref) \
        .execute()

    registros = []
    usados = set()

    # --------------------------------------------------
    # Palpite fixo
    # --------------------------------------------------
    fixo = gerar_palpite(
        pool,
        scores_combinacao,
        score_min,
        ultimos_numeros,
        fator_aprendizado
    )

    if not fixo:
        print("❌ Falha ao gerar palpite fixo")
        return

    usados.add(tuple(fixo))
    pares, impares, soma = calcular_metricas(fixo)

    registros.append({
        "data_referencia": hoje,
        "concurso_referencia": concurso_ref,
        "tipo": "fixo",
        "indice_palpite": 0,
        "numeros": json.dumps(fixo),
        "pares": pares,
        "impares": impares,
        "soma_total": soma,
        "metricas": json.dumps({
            "versao": VERSAO_GERADOR,
            "fonte_score": "historico_real",
            "aprendizado": "v3-global"
        })
    })

    # --------------------------------------------------
    # Palpites estatísticos
    # --------------------------------------------------
    for i in range(QTD_ESTATISTICOS):
        palpite = gerar_palpite(
            pool,
            scores_combinacao,
            score_min,
            ultimos_numeros,
            fator_aprendizado
        )

        if not palpite or tuple(palpite) in usados:
            continue

        usados.add(tuple(palpite))
        pares, impares, soma = calcular_metricas(palpite)

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "tipo": "estatistico",
            "indice_palpite": i + 1,
            "numeros": json.dumps(palpite),
            "pares": pares,
            "impares": impares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "fonte_score": "historico_real",
                "aprendizado": "v3-global"
            })
        })

    # --------------------------------------------------
    # Persistência
    # --------------------------------------------------
    supabase.table("palpites_validos").insert(registros).execute()

    print(f"✅ {len(registros)} palpites gerados com score real")
    print("🎯 Gerador V3 finalizado com aprendizado global real")


if __name__ == "__main__":
    main()

