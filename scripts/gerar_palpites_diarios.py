import sys
import random
import json
import numpy as np

from pathlib import Path
from datetime import datetime
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais


QTD_FINAL = 7
MAX_TENTATIVAS = 60000
VERSAO = "v9.9-anti-overfit"


def gerar_pool():
    return list(range(1, 26))


def gerar_jogo(pool):
    return sorted(random.sample(pool, 15))


def calcular_metricas(nums):
    pares = sum(n % 2 == 0 for n in nums)
    soma = sum(nums)

    linhas = [
        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),
    ]

    return pares, soma, linhas


def score_validacao(nums):
    pares, soma, linhas = calcular_metricas(nums)

    score = 1.0

    if pares < 5 or pares > 10:
        score *= 0.90

    if soma < 165 or soma > 220:
        score *= 0.85

    if max(linhas) > 4:
        score *= 0.90

    return score


def distancia(a, b):
    return len(set(a) ^ set(b))


def diversidade_ok(jogo, selecionados):
    for s in selecionados:
        if distancia(jogo, s) < 6:
            return False
    return True


def estrutura_linhas(nums):
    return tuple(calcular_metricas(nums)[2])


def calcular_score_final(
    nums,
    base_scores,
    rec_scores,
    fator,
    ultimo_concurso
):
    chave = tuple(nums)

    media_base = np.mean(list(base_scores.values())) if base_scores else 0.5
    media_rec = np.mean(list(rec_scores.values())) if rec_scores else 0.5

    base = base_scores.get(chave, media_base)
    rec = rec_scores.get(chave, media_rec)

    score = (base * 0.55) + (rec * 0.45)

    repetidos = len(set(nums) & set(ultimo_concurso))

    if repetidos >= 10:
        score *= 0.80
    elif repetidos >= 8:
        score *= 0.90

    score *= score_validacao(nums)

    score *= fator

    score *= (1 + np.random.normal(0, 0.02))

    return max(score, 0.01)


def main():

    supabase = get_supabase()

    hoje = datetime.now().date().isoformat()

    print(f"\n🚀 Gerador {VERSAO} iniciado em {hoje}")

    concurso = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
        .data
    )[0]

    concurso_ref = concurso["concurso"]

    dezenas = concurso["dezenas"]

    if isinstance(dezenas, str):
        ultimo = json.loads(dezenas)
    else:
        ultimo = dezenas

    ultimo = [int(x) for x in ultimo]

    print(f"📌 Concurso: {concurso_ref}")

    fator = obter_fator_aprendizado_global()["fator"]

    print(f"🧠 Fator: {fator}")

    base_scores, rec_scores = calcular_score_combinacoes_reais()

    pool = gerar_pool()

    candidatos = []
    vistos = set()

    for _ in range(MAX_TENTATIVAS):

        if len(candidatos) >= 3000:
            break

        jogo = gerar_jogo(pool)

        key = tuple(jogo)

        if key in vistos:
            continue

        vistos.add(key)

        score = calcular_score_final(
            jogo,
            base_scores,
            rec_scores,
            fator,
            ultimo
        )

        candidatos.append({
            "nums": jogo,
            "score": score
        })

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    finais = []

    freq_global = Counter()

    estruturas = set()

    for candidato in candidatos:

        nums = candidato["nums"]

        estrutura = estrutura_linhas(nums)

        if estrutura in estruturas:
            continue

        penalidade = 1.0

        for n in nums:
            if freq_global[n] >= 3:
                penalidade *= 0.96

        candidato["score"] *= penalidade

        if diversidade_ok(
            nums,
            [x["nums"] for x in finais]
        ):

            finais.append(candidato)

            estruturas.add(estrutura)

            for n in nums:
                freq_global[n] += 1

        if len(finais) == QTD_FINAL:
            break

    usados = set()

    for p in finais:
        usados.update(p["nums"])

    faltantes = set(range(1, 26)) - usados

    if faltantes:
        print(f"♻️ Ajustando cobertura: {sorted(faltantes)}")

    print("\n🏆 FINAL:")

    for i, p in enumerate(finais, start=1):

        print(
            f"{i}º | score={round(p['score'],4)} | {p['nums']}"
        )

    print("\n💾 Salvando...")

    payload = []

    for i, p in enumerate(finais, start=1):

        pares, soma, _ = calcular_metricas(
            p["nums"]
        )

        payload.append({
            "data_referencia": hoje,
            "concurso_referencia": concurso_ref,
            "indice_palpite": i,
            "tipo": "fixo" if i == 1 else "estatistico",
            "numeros": p["nums"],
            "pares": pares,
            "impares": 15 - pares,
            "soma_total": soma,
            "acertos": None,
            "versao_gerador": VERSAO,
            "metricas": {
                "score": round(float(p["score"]), 6)
            }
        })

    (
        supabase
        .table("palpites_validos")
        .delete()
        .eq("concurso_referencia", concurso_ref)
        .execute()
    )

    (
        supabase
        .table("palpites_validos")
        .insert(payload)
        .execute()
    )

    print(f"✅ {len(payload)} palpites gravados")
    print(f"\n✅ {VERSAO} concluída")


if __name__ == "__main__":
    main()
