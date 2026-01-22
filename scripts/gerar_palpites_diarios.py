import sys
import json
import random
from pathlib import Path
from datetime import datetime
from collections import defaultdict

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
# Configurações — AJUSTADAS E REALISTAS
# ======================================================
VERSAO_GERADOR = "v3.5-score-real-estavel"
QTD_ESTATISTICOS = 6
MAX_TENTATIVAS = 25000

SOMA_MIN = 155
SOMA_MAX = 225

PARES_MIN = 5
PARES_MAX = 10

SEQ_MAX = 7   # ❗ NÃO rígido (corrigido conforme observado)

LINHA_MIN = 0
LINHA_MAX = 6

REPET_MIN = 6
REPET_MAX = 13

PERCENTIL_MIN = 0.30
SCORE_FLOOR = 0.01

# ======================================================
# Funções auxiliares
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    impares = 15 - pares
    soma = sum(nums)
    return pares, impares, soma


def max_sequencia(nums):
    atual = max_seq = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            max_seq = max(max_seq, atual)
        else:
            atual = 1
    return max_seq


def distribuicao_linhas(nums):
    linhas = [
        range(1, 6),
        range(6, 11),
        range(11, 16),
        range(16, 21),
        range(21, 26),
    ]
    return [sum(1 for n in nums if n in r) for r in linhas]


def finais_ok(nums):
    finais = defaultdict(int)
    for n in nums:
        finais[n % 10] += 1
    return max(finais.values()) <= 4


def repeticao_ok(nums, ultimos):
    repetidos = len(set(nums) & set(ultimos))
    return REPET_MIN <= repetidos <= REPET_MAX


# ======================================================
# Validação principal
# ======================================================
def validar(nums, scores_combinacao, score_min, ultimos, fator_aprendizado):
    if len(nums) != 15:
        return False

    pares, _, soma = calcular_metricas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False

    if not (PARES_MIN <= pares <= PARES_MAX):
        return False

    if max_sequencia(nums) > SEQ_MAX:
        return False

    if not finais_ok(nums):
        return False

    if not repeticao_ok(nums, ultimos):
        return False

    linhas = distribuicao_linhas(nums)
    if not all(LINHA_MIN <= x <= LINHA_MAX for x in linhas):
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
# Geração de palpite
# ======================================================
def gerar_palpite(pool, scores_combinacao, score_min, ultimos, fator):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(set(random.sample(pool, 15)))
        if len(nums) != 15:
            continue
        if validar(nums, scores_combinacao, score_min, ultimos, fator):
            return nums
    return None


# ======================================================
# Execução principal
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    # --------------------------------------------------
    # Último concurso
    # --------------------------------------------------
    concurso = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    ).data[0]

    concurso_ref = concurso["concurso"]
    ultimos_numeros = list(map(int, concurso["dezenas"]))

    # --------------------------------------------------
    # Pool de números — LIMPO
    # --------------------------------------------------
    raw_pool = [
        r["numero"] for r in
        supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .execute().data
    ]

    pool = sorted(set(raw_pool))
    if len(pool) < 15:
        pool = list(range(1, 26))

    # --------------------------------------------------
    # Aprendizado global
    # --------------------------------------------------
    aprendizado = obter_fator_aprendizado_global()
    fator = aprendizado["fator"]
    print(f"🧠 Fator de aprendizado global: {fator}")

    # --------------------------------------------------
    # Score real histórico
    # --------------------------------------------------
    scores_combinacao = calcular_score_combinacoes_reais()
    valores = sorted(scores_combinacao.values(), reverse=True)

    score_min = valores[int(len(valores) * PERCENTIL_MIN)] if valores else SCORE_FLOOR
    score_min = max(score_min, SCORE_FLOOR)

    print(f"📊 Score mínimo aplicado: {score_min}")

    # --------------------------------------------------
    # Limpeza
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
    fixo = gerar_palpite(pool, scores_combinacao, score_min, ultimos_numeros, fator)

    if not fixo:
        print("❌ Nenhum palpite viável encontrado")
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
            "aprendizado": "global-real"
        })
    })

    print(f"🎯 Palpite fixo gerado | {fixo}")

    # --------------------------------------------------
    # Estatísticos
    # --------------------------------------------------
    for i in range(QTD_ESTATISTICOS):
        p = gerar_palpite(pool, scores_combinacao, score_min, ultimos_numeros, fator)
        if not p or tuple(p) in usados:
            continue

        usados.add(tuple(p))
        pares, impares, soma = calcular_metricas(p)

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "tipo": "estatistico",
            "indice_palpite": i + 1,
            "numeros": json.dumps(p),
            "pares": pares,
            "impares": impares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "aprendizado": "global-real"
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print(f"✅ {len(registros)} palpites gerados")
    print("🏁 Gerador finalizado com estabilidade total\n")


if __name__ == "__main__":
    main()




