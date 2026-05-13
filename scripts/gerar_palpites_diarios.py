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
    extrair_estrutura
)

VERSAO = "v15.3-restaurado"
QTD_FINAL = 7
MAX_TENTATIVAS = 120000

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}

MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15, 16, 20,
    21, 22, 23, 24, 25
}


# ======================================================
# UTIL
# ======================================================
def media_segura(v, f=0.5):
    return float(np.mean(v)) if v else f


def calcular_filtros(nums, ultimo):
    pares = sum(1 for n in nums if n % 2 == 0)
    primos = sum(1 for n in nums if n in PRIMOS)
    moldura = sum(1 for n in nums if n in MOLDURA)
    soma = sum(nums)
    repetidos = len(set(nums) & set(ultimo))

    seq_max = atual = 1
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


def validar(f):
    return (
        165 <= f["soma"] <= 210 and
        7 <= f["pares"] <= 9 and
        4 <= f["primos"] <= 7 and
        9 <= f["moldura"] <= 12 and
        8 <= f["repetidos"] <= 10 and
        f["seq_max"] <= 4
    )


# ======================================================
# SCORES (RESTAURADO)
# ======================================================
def score_dezenas(j, base):
    return media_segura([base.get((n,), 0.5) for n in j])


def score_pares(j, base):
    vals = []
    for p in itertools.combinations(j, 2):
        v = base.get(tuple(sorted(p)))
        if v is not None:
            vals.append(v)
    return media_segura(vals, 0.45)


def score_trincas(j, base):
    vals = []
    for t in itertools.combinations(j, 3):
        v = base.get(tuple(sorted(t)))
        if v is not None:
            vals.append(v)
    return media_segura(vals, 0.42)


# ======================================================
# MEMÓRIA (RESTAURADA DE VERDADE)
# ======================================================
def bonus_memoria(mem):
    if not mem:
        return 1.0

    bonus = 1.0
    score = float(mem.get("score_medio_real", 0))
    vezes = int(mem.get("vezes_gerado", 0))

    if score > 0:
        bonus *= 1.08
    if vezes >= 8 and score == 0:
        bonus *= 0.85
    if 1 <= vezes <= 3 and score >= 1:
        bonus *= 1.10

    return bonus


# ======================================================
# SCORE FINAL (AGORA DIFERENCIA OS JOGOS)
# ======================================================
def score_total(jogo, base_scores, fator_global, mem):
    s1 = score_dezenas(jogo, base_scores)
    s2 = score_pares(jogo, base_scores)
    s3 = score_trincas(jogo, base_scores)

    base = (s1 * 0.25) + (s2 * 0.35) + (s3 * 0.40)

    # ruído leve controlado (evita empates)
    ruido = random.uniform(0.985, 1.015)

    return base * fator_global * bonus_memoria(mem) * ruido


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print(f"🛡️ {VERSAO}")

    fuso = pytz.timezone("America/Sao_Paulo")
    hoje = datetime.now(fuso).date().isoformat()

    hist = carregar_historico()
    ultimo = hist[-1]["numeros"]
    concurso_ref = int(hist[-1]["concurso"]) + 1

    base_scores, _ = calcular_score_combinacoes_reais()
    fator_global = obter_fator_aprendizado_global()["fator"]

    memoria = {
        m["hash_estrutura"]: m
        for m in supabase.table("memoria_cenarios").select("*").execute().data
    }

    usados = set(tuple(sorted(h["numeros"])) for h in hist)

    candidatos = []
    pool = list(range(1, 26))

    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 5000:
            break

        jogo = sorted(random.sample(pool, 15))

        if tuple(jogo) in usados:
            continue

        f = calcular_filtros(jogo, ultimo)

        if not validar(f):
            continue

        estr = extrair_estrutura(jogo)
        mem = memoria.get(estr["hash_estrutura"])

        score = score_total(jogo, base_scores, fator_global, mem)

        candidatos.append({
            "nums": jogo,
            "score": score,
            "filtros": f,
            "mem": bool(mem)
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
    telegram = []

    for i, c in enumerate(finais, 1):

        linha = f"{i}º | {c['score']:.6f} | {c['nums']}"
        print(linha)
        telegram.append(linha)

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
                "memoria": c["mem"]
            }
        })

    supabase.table("palpites_validos") \
        .delete().eq("concurso_referencia", concurso_ref).execute()

    supabase.table("palpites_validos") \
        .upsert(payload, on_conflict="concurso_referencia,indice_palpite") \
        .execute()

    print("\n📲 TELEGRAM_PAYLOAD_START")
    print("\n".join(telegram))
    print("📲 TELEGRAM_PAYLOAD_END")


if __name__ == "__main__":
    main()
