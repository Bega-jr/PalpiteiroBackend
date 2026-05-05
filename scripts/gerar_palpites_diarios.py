import sys
import random
import json
import numpy as np
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase
from app.services.aprendizado_service_v3 import obter_fator_aprendizado_global
from app.services.estatisticas_combinacao_v3 import calcular_score_combinacoes_reais


QTD_FINAL = 7
MAX_TENTATIVAS = 60000
VERSAO = "v9.8.3-discriminativo"


def gerar_pool(supabase):
    data = (
        supabase
        .table("estatisticas_numeros")
        .select("numero")
        .execute()
        .data
    )

    pool = sorted(
        set(
            int(r["numero"])
            for r in data
            if r.get("numero") is not None
        )
    )

    print(f"\n📊 POOL: {len(pool)} números -> {pool}")

    if len(pool) < 15:
        raise ValueError("POOL INVÁLIDO")

    return pool


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
    score -= abs(7 - pares) * 0.03

    if soma < 165 or soma > 220:
        score -= 0.12

    if max(linhas) > 4:
        score -= (max(linhas) - 4) * 0.02

    return max(score, 0.25)


def distancia(a, b):
    return len(set(a) ^ set(b))


def diversidade_ok(jogo, selecionados):
    return all(distancia(jogo, s) >= 5 for s in selecionados)


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

    score = (base * 0.60) + (rec * 0.40)

    score *= (1 + np.random.normal(0, 0.025))

    repetidos = len(set(nums) & set(ultimo_concurso))
    score *= (1 - (repetidos / 30))

    score *= score_validacao(nums)
    score *= fator

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
    )

    concurso_ref = concurso[0]["concurso"]

    dezenas_raw = concurso[0]["dezenas"]

    if isinstance(dezenas_raw, str):
        ultimo = json.loads(dezenas_raw)
    else:
        ultimo = dezenas_raw

    ultimo = [int(x) for x in ultimo]

    print(f"📌 Concurso: {concurso_ref}")

    pool = gerar_pool(supabase)

    fator = obter_fator_aprendizado_global()["fator"]
    print(f"🧠 Fator: {round(fator,4)}")

    base_scores, rec_scores = calcular_score_combinacoes_reais()

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

    print(f"✅ candidatos válidos: {len(candidatos)}")

    candidatos.sort(
        key=lambda x: x["score"],
        reverse=True
    )

    finais = []

    for candidato in candidatos:

        if diversidade_ok(
            candidato["nums"],
            [x["nums"] for x in finais]
        ):
            finais.append(candidato)

        if len(finais) == QTD_FINAL:
            break

    print("\n🏆 FINAL:")

    for i, p in enumerate(finais, start=1):
        print(
            f"{i}º | score={round(p['score'],4)} | {p['nums']}"
        )

    print("\n💾 Salvando no Supabase...")

    (
        supabase
        .table("palpites_validos")
        .delete()
        .eq("concurso_referencia", concurso_ref)
        .execute()
    )

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
                "versao": VERSAO,
                "score": round(float(p["score"]), 6)
            }
        })

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
