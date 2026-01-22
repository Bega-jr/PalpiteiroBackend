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
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais,
    extrair_metricas_jogo
)

# ======================================================
# CONFIGURAÇÕES – v3.1 ESTÁVEL
# ======================================================
VERSAO_GERADOR = "v3.1-score-real-estavel"
QTD_ESTATISTICOS = 6
MAX_TENTATIVAS = 20000

SOMA_MIN = 155
SOMA_MAX = 225

PARES_MIN = 5
PARES_MAX = 10

REPET_MIN = 6
REPET_MAX = 12

SEQ_LINHA_MAX = 4          # sequência MÁXIMA dentro da mesma linha
PESO_SEQ_LINHA = 0.08      # penalização suave

LINHA_MIN = 1
LINHA_MAX = 5

PERCENTIL_INICIAL = 0.30
RELAX_FATOR = 0.7
MAX_RELAX = 5

# ======================================================
# FUNÇÕES AUXILIARES
# ======================================================
def calcular_metricas_basicas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def repeticao_ok(nums, ultimos):
    rep = len(set(nums) & set(ultimos))
    return REPET_MIN <= rep <= REPET_MAX


def distribuicao_linhas(nums):
    return (
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    )


def linhas_ok(nums):
    return all(LINHA_MIN <= x <= LINHA_MAX for x in distribuicao_linhas(nums))


def max_sequencia_por_linha(nums):
    linhas = {
        1: [n for n in nums if 1 <= n <= 5],
        2: [n for n in nums if 6 <= n <= 10],
        3: [n for n in nums if 11 <= n <= 15],
        4: [n for n in nums if 16 <= n <= 20],
        5: [n for n in nums if 21 <= n <= 25],
    }

    def max_seq(lista):
        if len(lista) < 2:
            return 1
        seq = atual = 1
        for i in range(1, len(lista)):
            if lista[i] == lista[i - 1] + 1:
                atual += 1
                seq = max(seq, atual)
            else:
                atual = 1
        return seq

    return max(max_seq(sorted(v)) for v in linhas.values())


# ======================================================
# VALIDAÇÃO PRINCIPAL (SOFT)
# ======================================================
def validar(nums, scores, score_min, ultimos, fator_aprendizado):
    pares, soma = calcular_metricas_basicas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
    if not (PARES_MIN <= pares <= PARES_MAX):
        return False
    if not linhas_ok(nums):
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

    score = scores.get(chave, 0) * fator_aprendizado

    # Penalização suave por sequência na mesma linha
    seq_linha = max_sequencia_por_linha(nums)
    if seq_linha > SEQ_LINHA_MAX:
        score -= PESO_SEQ_LINHA

    return score >= score_min


# ======================================================
# GERADOR COM FALLBACK
# ======================================================
def gerar_palpite(pool, scores, score_min, ultimos, fator_aprendizado):
    tentativas_relax = 0
    score_atual = score_min

    while tentativas_relax <= MAX_RELAX:
        for _ in range(MAX_TENTATIVAS):
            nums = sorted(random.sample(pool, 15))
            if validar(nums, scores, score_atual, ultimos, fator_aprendizado):
                return nums

        score_atual *= RELAX_FATOR
        tentativas_relax += 1
        print(f"⚠️ Relaxando score mínimo para {round(score_atual, 4)}")

    return None


# ======================================================
# EXECUÇÃO PRINCIPAL
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    # Último concurso
    concurso = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    ).data[0]

    concurso_ref = concurso["concurso"]
    ultimos = list(map(int, concurso["dezenas"]))

    # Pool (top 20 números)
    estat = (
        supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(20)
        .execute()
    ).data

    pool = [n["numero"] for n in estat]

    # Aprendizado global
    aprendizado = obter_fator_aprendizado_global()
    fator = aprendizado["fator"]

    print(f"🧠 Fator de aprendizado global: {fator}")

    # Score real histórico
    scores = calcular_score_combinacoes_reais()
    valores = sorted(scores.values(), reverse=True)

    corte = int(len(valores) * PERCENTIL_INICIAL)
    score_min = valores[corte]

    print(f"📊 Score mínimo aplicado: {score_min}")

    # Limpeza
    supabase.table("palpites_validos") \
        .delete() \
        .eq("concurso_referencia", concurso_ref) \
        .execute()

    registros = []
    usados = set()

    # Palpite fixo
    fixo = gerar_palpite(pool, scores, score_min, ultimos, fator)
    if not fixo:
        print("❌ Falha crítica evitada: nenhuma validação passou, mas sistema não travou")
        return

    usados.add(tuple(fixo))
    pares, soma = calcular_metricas_basicas(fixo)

    registros.append({
        "data_referencia": hoje,
        "concurso_referencia": concurso_ref,
        "tipo": "fixo",
        "indice_palpite": 0,
        "numeros": json.dumps(fixo),
        "pares": pares,
        "impares": 15 - pares,
        "soma_total": soma,
        "metricas": json.dumps({
            "versao": VERSAO_GERADOR,
            "aprendizado": "v3-global",
            "sequencia": "soft-por-linha"
        })
    })

    # Estatísticos
    for i in range(QTD_ESTATISTICOS):
        palpite = gerar_palpite(pool, scores, score_min, ultimos, fator)
        if not palpite or tuple(palpite) in usados:
            continue

        usados.add(tuple(palpite))
        pares, soma = calcular_metricas_basicas(palpite)

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "tipo": "estatistico",
            "indice_palpite": i + 1,
            "numeros": json.dumps(palpite),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "aprendizado": "v3-global",
                "sequencia": "soft-por-linha"
            })
        })

    supabase.table("palpites_validos").insert(registros).execute()

    print(f"✅ {len(registros)} palpites gerados com sucesso")
    print("🎯 Gerador finalizado com estabilidade total")


if __name__ == "__main__":
    main()

