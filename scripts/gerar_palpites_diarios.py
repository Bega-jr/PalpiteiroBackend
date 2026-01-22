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
# Configuração ESTÁVEL (produção)
# ======================================================
QTD_ESTATISTICOS = 6
VERSAO_GERADOR = "v3.1-score-real-estavel"
MAX_TENTATIVAS = 20000

# Limites base
SOMA_MIN, SOMA_MAX = 150, 230
PARES_MIN, PARES_MAX = 5, 10
SEQ_MAX = 5
REPET_MIN, REPET_MAX = 6, 13
LINHA_MIN, LINHA_MAX = 0, 6

PERCENTIL_MIN = 0.20   # MUITO importante
SCORE_FALLBACK = 0.05  # score mínimo absoluto

# ======================================================
# Auxiliares
# ======================================================
def calcular_metricas(nums):
    pares = sum(1 for n in nums if n % 2 == 0)
    soma = sum(nums)
    return pares, soma


def max_sequencia(nums):
    atual = seq = 1
    for i in range(1, len(nums)):
        atual = atual + 1 if nums[i] == nums[i - 1] + 1 else 1
        seq = max(seq, atual)
    return seq


def linhas_ok(nums):
    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]
    return all(LINHA_MIN <= x <= LINHA_MAX for x in linhas)


def repeticao_ok(nums, ultimos):
    r = len(set(nums) & set(ultimos))
    return REPET_MIN <= r <= REPET_MAX


# ======================================================
# Validação INTELIGENTE
# ======================================================
def validar(nums, scores, score_min, ultimos, fator):
    pares, soma = calcular_metricas(nums)

    if not (SOMA_MIN <= soma <= SOMA_MAX):
        return False
    if not (PARES_MIN <= pares <= PARES_MAX):
        return False
    if max_sequencia(nums) > SEQ_MAX:
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

    # ⚠️ Se não existe no histórico → aceita com score base
    score_base = scores.get(chave, SCORE_FALLBACK)

    score_final = score_base * fator
    return score_final >= score_min


# ======================================================
# Gerador com Fallback REAL
# ======================================================
def gerar_palpite(pool, scores, score_min, ultimos, fator):
    score_atual = score_min

    for etapa in range(3):
        for _ in range(MAX_TENTATIVAS // 3):
            nums = sorted(random.sample(pool, 15))
            if validar(nums, scores, score_atual, ultimos, fator):
                return nums

        # Relaxamento progressivo
        score_atual *= 0.7
        print(f"⚠️ Relaxando score mínimo para {round(score_atual, 4)}")

    return None


# ======================================================
# Execução principal
# ======================================================
def main():
    supabase = get_supabase()
    hoje = datetime.now().date().isoformat()

    print(f"🚀 Gerador {VERSAO_GERADOR} iniciado em {hoje}")

    ultimo = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
    ).data[0]

    concurso_ref = ultimo["concurso"]
    ultimos_numeros = list(map(int, ultimo["dezenas"]))

    estat = (
        supabase.table("estatisticas_numeros")
        .select("numero")
        .order("score", desc=True)
        .limit(22)
        .execute()
    ).data

    pool = [n["numero"] for n in estat]

    aprendizado = obter_fator_aprendizado_global()
    fator = aprendizado["fator"]
    print(f"🧠 Fator de aprendizado global: {fator}")

    scores = calcular_score_combinacoes_reais()
    valores = sorted(scores.values(), reverse=True)

    if valores:
        corte = int(len(valores) * PERCENTIL_MIN)
        score_min = max(valores[corte], SCORE_FALLBACK)
    else:
        score_min = SCORE_FALLBACK

    print(f"📊 Score mínimo aplicado: {score_min}")

    supabase.table("palpites_validos") \
        .delete() \
        .eq("concurso_referencia", concurso_ref) \
        .execute()

    registros = []
    usados = set()

    for i in range(QTD_ESTATISTICOS + 1):
        palpite = gerar_palpite(pool, scores, score_min, ultimos_numeros, fator)

        if not palpite or tuple(palpite) in usados:
            continue

        usados.add(tuple(palpite))
        pares, soma = calcular_metricas(palpite)

        registros.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "tipo": "fixo" if i == 0 else "estatistico",
            "indice_palpite": i,
            "numeros": json.dumps(palpite),
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "metricas": json.dumps({
                "versao": VERSAO_GERADOR,
                "aprendizado": "v3-global",
                "fallback": True
            })
        })

    if not registros:
        print("❌ Falha crítica evitada: nenhuma validação passou, mas sistema não travou")
        return

    supabase.table("palpites_validos").insert(registros).execute()
    print(f"✅ {len(registros)} palpites gerados com sucesso")


if __name__ == "__main__":
    main()

