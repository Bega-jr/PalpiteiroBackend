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
# Configurações Gerais
# ======================================================
VERSAO_GERADOR = "v3.2-score-real-estavel"
QTD_ESTATISTICOS = 6
MAX_TENTATIVAS = 20000

# Regras numéricas (flexíveis e reais)
SOMA_MIN, SOMA_MAX = 150, 230
PARES_MIN, PARES_MAX = 5, 10
SEQ_MAX_GLOBAL = 6     # sequência total
SEQ_MAX_LINHA = 5      # sequência dentro da mesma linha
REPET_MIN, REPET_MAX = 7, 12
LINHA_MIN, LINHA_MAX = 1, 5

# Score
PERCENTIL_INICIAL = 0.20
SCORE_NEUTRO = 0.05    # quando não existe histórico

# ======================================================
# Funções auxiliares
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def max_sequencia(nums):
    atual = seq = 1
    for i in range(1, len(nums)):
        if nums[i] == nums[i - 1] + 1:
            atual += 1
            seq = max(seq, atual)
        else:
            atual = 1
    return seq


def sequencia_por_linha(nums):
    linhas = {
        1: [n for n in nums if 1 <= n <= 5],
        2: [n for n in nums if 6 <= n <= 10],
        3: [n for n in nums if 11 <= n <= 15],
        4: [n for n in nums if 16 <= n <= 20],
        5: [n for n in nums if 21 <= n <= 25],
    }

    maior = 1
    for l in linhas.values():
        l = sorted(l)
        maior = max(maior, max_sequencia(l) if l else 1)
    return maior


def linhas_ok(nums):
    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]
    return all(LINHA_MIN <= x <= LINHA_MAX for x in linhas)


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
def validar(nums, scores, score_min, ultimos, fator):
    pares, soma = calcular_metricas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
    if not (PARES_MIN <= pares <= PARES_MAX):
        return False
    if max_sequencia(nums) > SEQ_MAX_GLOBAL:
        return False
    if sequencia_por_linha(nums) > SEQ_MAX_LINHA:
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

    base = scores.get(chave)
    score_final = (base if base is not None else SCORE_NEUTRO) * fator

    return score_final >= score_min


# ======================================================
# Geração controlada
# ======================================================
def gerar_palpite(pool, scores, score_min, ultimos, fator):
    for _ in range(MAX_TENTATIVAS):
        nums = sorted(random.sample(pool, 15))
        if validar(nums, scores, score_min, ultimos, fator):
            return nums
    return None


# ======================================================
# Execução principal
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

    # Pool ampliado
    estat = (
        supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(30)
        .execute()
    ).data

    pool = [n["numero"] for n in estat]

    # Aprendizado global
    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator de aprendizado global: {fator}")

    # Scores reais
    scores = calcular_score_combinacoes_reais()
    valores = sorted(scores.values(), reverse=True)

    score_min = valores[int(len(valores) * PERCENTIL_INICIAL)] if valores else 0.03
    print(f"📊 Score mínimo aplicado: {round(score_min,4)}")

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
    pares, soma = calcular_metricas(fixo)

    registros.append({
        "data_referencia": hoje,
        "concurso_referencia": concurso_ref,
        "tipo": "fixo",
        "indice_palpite": 0,
        "numeros": json.dumps(fixo),
        "pares": pares,
        "impares": 15 - pares,
        "soma_total": soma,
        "metricas": json.dumps({"versao": VERSAO_GERADOR})
    })

    # Estatísticos
    for i in range(QTD_ESTATISTICOS):
        p = gerar_palpite(pool, scores, score_min, ultimos, fator)
        if not p or tuple(p) in usados:
            continue
        usados.add(tuple(p))
        pares, soma = calcular_metricas(p)

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "tipo": "estatistico",
            "indice_palpite": i + 1,
            "numeros": json.dumps(p),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "metricas": json.dumps({"versao": VERSAO_GERADOR})
        })

    supabase.table("palpites_validos").insert(registros).execute()
    print(f"✅ {len(registros)} palpites gerados com sucesso")


if __name__ == "__main__":
    main()


