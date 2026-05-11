import sys
import json
import random
import itertools
import numpy as np
import pytz

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

from scripts.processamento_diario_lotofacil import (
    carregar_historico,
    extrair_estrutura,
    buscar_cenario_similar
)

VERSAO = "v13.8-triple-context-rare"

QTD_FINAL = 7
MAX_TENTATIVAS = 100000


# ======================================================
# REGRAS ESTATÍSTICAS
# ======================================================
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

MOLDURA = {
    1,2,3,4,5,
    6,10,11,15,16,20,
    21,22,23,24,25
}


# ======================================================
# AUXILIARES
# ======================================================
def media_segura(valores, fallback=0.5):
    if not valores:
        return fallback
    return float(np.mean(valores))


def calcular_filtros(nums, ultimo_concurso):
    pares = sum(1 for n in nums if n % 2 == 0)

    primos = sum(1 for n in nums if n in PRIMOS)

    moldura = sum(1 for n in nums if n in MOLDURA)

    soma = sum(nums)

    repetidos = len(set(nums) & set(ultimo_concurso))

    # sequência máxima
    seq_max = 1
    atual = 1

    for i in range(len(nums) - 1):
        if nums[i+1] == nums[i] + 1:
            atual += 1
            seq_max = max(seq_max, atual)
        else:
            atual = 1

    return {
        "pares": pares,
        "primos": primos,
        "moldura": moldura,
        "soma": soma,
        "repetidos": repetidos,
        "seq_max": seq_max
    }


def validar_jogo(f):
    if not (165 <= f["soma"] <= 210):
        return False

    if not (7 <= f["pares"] <= 9):
        return False

    if not (4 <= f["primos"] <= 7):
        return False

    if not (9 <= f["moldura"] <= 12):
        return False

    if not (8 <= f["repetidos"] <= 10):
        return False

    if f["seq_max"] > 4:
        return False

    return True


# ======================================================
# SCORE
# ======================================================
def score_dezenas(jogo, base_scores):
    valores = []

    for n in jogo:
        valores.append(base_scores.get((n,), 0.5))

    return media_segura(valores)


def score_pares(jogo, base_scores):
    valores = []

    for par in itertools.combinations(jogo, 2):
        score = base_scores.get(tuple(sorted(par)))

        if score is not None:
            valores.append(score)

    # fallback contextual
    if not valores:
        return 0.45

    return media_segura(valores)


def score_trincas(jogo, base_scores):
    valores = []

    for trio in itertools.combinations(jogo, 3):
        score = base_scores.get(tuple(sorted(trio)))

        if score is not None:
            valores.append(score)

    # fallback contextual
    if not valores:
        return 0.42

    return media_segura(valores)


# ======================================================
# SCORE MEMÓRIA
# ======================================================
def bonus_memoria(supabase, jogo):
    estrutura = extrair_estrutura(jogo)

    memoria = buscar_cenario_similar(
        supabase=supabase,
        estrutura=estrutura
    )

    if not memoria:
        return 1.0, False

    score_real = float(memoria.get("score_medio_real", 0))
    vezes = int(memoria.get("vezes_gerado", 0))

    bonus = 1.0

    # Cenário já premiado
    if score_real > 0:
        bonus *= 1.08

    # Saturação
    if vezes >= 8 and score_real == 0:
        bonus *= 0.85

    # Raridade com histórico bom
    if 1 <= vezes <= 3 and score_real >= 1:
        bonus *= 1.10

    return bonus, True


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print(f"🛡️ {VERSAO}")

    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()

    historico = carregar_historico()

    ultimo_real = historico[-1]["numeros"]

    concurso_ref = int(historico[-1]["concurso"]) + 1

    print(f"📌 Concurso alvo: {concurso_ref}")

    base_scores, _ = calcular_score_combinacoes_reais()

    fator_global = obter_fator_aprendizado_global()["fator"]

    print(f"🧠 Fator global: {fator_global:.4f}")

    vistos_historico = {
        tuple(sorted(h["numeros"]))
        for h in historico
    }

    candidatos = []

    universo_pool = list(range(1, 26))

    validos = 0

    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 5000:
            break

        jogo = sorted(random.sample(universo_pool, 15))

        if tuple(jogo) in vistos_historico:
            continue

        filtros = calcular_filtros(
            jogo,
            ultimo_real
        )

        if not validar_jogo(filtros):
            continue

        validos += 1

        s1 = score_dezenas(
            jogo,
            base_scores
        )

        s2 = score_pares(
            jogo,
            base_scores
        )

        s3 = score_trincas(
            jogo,
            base_scores
        )

        mem_bonus, mem_match = bonus_memoria(
            supabase,
            jogo
        )

        score_final = (
            (s1 * 0.25) +
            (s2 * 0.35) +
            (s3 * 0.40)
        )

        score_final *= fator_global
        score_final *= mem_bonus

        candidatos.append({
            "nums": jogo,
            "score": score_final,
            "filtros": filtros,
            "memoria_match": mem_match
        })

    universo_estimado = int(
        (validos / MAX_TENTATIVAS) * 3268760
    )

    print(f"📊 Universo filtrado: {universo_estimado}")

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    finais = []

    for cand in candidatos:

        conflito = False

        for existente in finais:

            diff = len(
                set(cand["nums"]) ^
                set(existente["nums"])
            )

            if diff < 10:
                conflito = True
                break

        if conflito:
            continue

        finais.append(cand)

        if len(finais) >= QTD_FINAL:
            break

    print("🏆 TOP 7")

    payload = []

    for i, cand in enumerate(finais, start=1):

        jogo = cand["nums"]

        f = cand["filtros"]

        print(
            f"{i}º | "
            f"{cand['score']:.4f} | "
            f"{jogo}"
        )

        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,

            "tipo": "fixo" if i == 1 else "estatistico",

            "numeros": json.dumps(jogo),

            "pares": f["pares"],
            "impares": 15 - f["pares"],
            "soma_total": f["soma"],

            "processado": False,
            "conferido": False,

            "versao_gerador": VERSAO,

            "metricas": {
                "score": round(cand["score"], 6),
                "universo_estimado": universo_estimado,
                "memoria_match": cand["memoria_match"],
                "primos": f["primos"],
                "moldura": f["moldura"]
            }
        })

    supabase.table("palpites_validos") \
        .delete() \
        .eq("data_referencia", hoje) \
        .eq("concurso_referencia", concurso_ref) \
        .execute()

    supabase.table("palpites_validos") \
        .upsert(
            payload,
            on_conflict="data_referencia,indice_palpite"
        ) \
        .execute()

    print(f"✅ {VERSAO} concluída")


if __name__ == "__main__":
    main()
