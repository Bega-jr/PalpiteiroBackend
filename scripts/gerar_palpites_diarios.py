import sys
import json
import random
import itertools
import numpy as np
import pytz

from pathlib import Path
from datetime import datetime, date

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais

from scripts.processamento_diario_lotofacil import (
    carregar_historico,
    extrair_estrutura
)

VERSAO = "v15-inteligente"
QTD_FINAL = 7
MAX_TENTATIVAS = 120000


# ======================================================
# REGRAS
# ======================================================
PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15, 16, 20,
    21, 22, 23, 24, 25
}


# ======================================================
# AUX
# ======================================================
def media_segura(valores, fallback=0.5):
    return float(np.mean(valores)) if valores else fallback


def calcular_filtros(nums, ultimo_concurso):
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in PRIMOS)
    moldura = sum(1 for n in nums if n in MOLDURA)
    soma = sum(nums)
    repetidos = len(set(nums) & set(ultimo_concurso))

    seq_max = 1
    atual = 1

    for i in range(len(nums) - 1):
        if nums[i + 1] == nums[i] + 1:
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
    return (
        165 <= f["soma"] <= 210 and
        7 <= f["pares"] <= 9 and
        4 <= f["primos"] <= 7 and
        9 <= f["moldura"] <= 12 and
        8 <= f["repetidos"] <= 10 and
        f["seq_max"] <= 4
    )


# ======================================================
# SCORES
# ======================================================
def score_dezenas(jogo, base_scores):
    return media_segura([base_scores.get((n,), 0.5) for n in jogo])


def score_pares(jogo, base_scores):
    vals = [base_scores.get(tuple(sorted(p))) for p in itertools.combinations(jogo, 2)]
    return media_segura([v for v in vals if v is not None], 0.45)


def score_trincas(jogo, base_scores):
    vals = [base_scores.get(tuple(sorted(t))) for t in itertools.combinations(jogo, 3)]
    return media_segura([v for v in vals if v is not None], 0.42)


# ======================================================
# MEMÓRIA
# ======================================================
def calcular_bonus_memoria(memoria):
    if not memoria:
        return 1.0

    bonus = 1.0
    score = float(memoria.get("score_medio_real", 0))
    vezes = int(memoria.get("vezes_gerado", 0))

    if score > 0:
        bonus *= 1.08
    if vezes >= 8 and score == 0:
        bonus *= 0.85
    if 1 <= vezes <= 3 and score >= 1:
        bonus *= 1.10

    return bonus


def validar_diversidade(hash_estrutura, memoria, usadas):
    score = float(memoria.get("score_medio_real", 0)) if memoria else 0
    vezes = int(memoria.get("vezes_gerado", 0)) if memoria else 0

    limite = 3 if score >= 0.25 else 1

    if usadas.get(hash_estrutura, 0) >= limite:
        return False

    usadas[hash_estrutura] = usadas.get(hash_estrutura, 0) + 1
    return True


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

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    memorias = supabase.table("memoria_cenarios").select("*").execute().data
    memoria_index = {m["hash_estrutura"]: m for m in memorias}

    vistos = {tuple(sorted(h["numeros"])) for h in historico}

    candidatos = []
    usadas = {}

    pool = list(range(1, 26))

    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 5000:
            break

        jogo = sorted(random.sample(pool, 15))

        if tuple(jogo) in vistos:
            continue

        filtros = calcular_filtros(jogo, ultimo_real)

        if not validar_jogo(filtros):
            continue

        estrutura = extrair_estrutura(jogo)
        memoria = memoria_index.get(estrutura["hash_estrutura"])

        if not validar_diversidade(estrutura["hash_estrutura"], memoria, usadas):
            continue

        s = (
            score_dezenas(jogo, base_scores) * 0.25 +
            score_pares(jogo, base_scores) * 0.35 +
            score_trincas(jogo, base_scores) * 0.40
        )

        score_final = s * fator_global * calcular_bonus_memoria(memoria)

        candidatos.append({
            "nums": jogo,
            "score": score_final,
            "filtros": filtros
        })

    candidatos.sort(key=lambda x: x["score"], reverse=True)

    finais = []

    for c in candidatos:
        if len(finais) >= QTD_FINAL:
            break

        if all(len(set(c["nums"]) ^ set(f["nums"])) >= 10 for f in finais):
            finais.append(c)

    print("🏆 TOP 7")

    payload = []

    for i, c in enumerate(finais, 1):
        print(f"{i}º | {c['score']:.4f} | {c['nums']}")

        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": json.dumps(c["nums"]),
            "pares": c["filtros"]["pares"],
            "impares": 15 - c["filtros"]["pares"],
            "soma_total": c["filtros"]["soma"],
            "processado": False,
            "conferido": False,
            "versao_gerador": VERSAO,
            "metricas": {
                "score": round(c["score"], 6),
                "primos": c["filtros"]["primos"],
                "moldura": c["filtros"]["moldura"]
            }
        })

    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    supabase.table("palpites_validos") \
        .upsert(payload, on_conflict="concurso_referencia,indice_palpite") \
        .execute()

    print(f"✅ {VERSAO} concluída")


if __name__ == "__main__":
    main()
