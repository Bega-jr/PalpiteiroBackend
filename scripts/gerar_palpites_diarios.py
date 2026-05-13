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
    extrair_estrutura,
    buscar_cenario_similar
)

VERSAO = "v14.1-context-recency-diversidade"

QTD_FINAL = 7
MAX_TENTATIVAS = 100000


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

    if not valores:
        return fallback

    return float(np.mean(valores))


def calcular_filtros(nums, ultimo_concurso):

    pares = sum(
        1 for n in nums
        if n % 2 == 0
    )

    primos = sum(
        1 for n in nums
        if n in PRIMOS
    )

    moldura = sum(
        1 for n in nums
        if n in MOLDURA
    )

    soma = sum(nums)

    repetidos = len(
        set(nums) &
        set(ultimo_concurso)
    )

    seq_max = 1
    atual = 1

    for i in range(len(nums) - 1):

        if nums[i + 1] == nums[i] + 1:

            atual += 1

            seq_max = max(
                seq_max,
                atual
            )

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
# SCORES
# ======================================================
def score_dezenas(jogo, base_scores):

    valores = []

    for n in jogo:

        valores.append(
            base_scores.get(
                (n,),
                0.5
            )
        )

    return media_segura(valores)


def score_pares(jogo, base_scores):

    valores = []

    for par in itertools.combinations(jogo, 2):

        score = base_scores.get(
            tuple(sorted(par))
        )

        if score is not None:

            valores.append(
                score
            )

    return media_segura(
        valores,
        0.45
    )


def score_trincas(jogo, base_scores):

    valores = []

    for trio in itertools.combinations(jogo, 3):

        score = base_scores.get(
            tuple(sorted(trio))
        )

        if score is not None:

            valores.append(
                score
            )

    return media_segura(
        valores,
        0.42
    )


# ======================================================
# MEMÓRIA
# ======================================================
def calcular_bonus_memoria(memoria):

    if not memoria:
        return 1.0, False

    bonus = 1.0

    score_real = float(
        memoria.get(
            "score_medio_real",
            0
        )
    )

    vezes = int(
        memoria.get(
            "vezes_gerado",
            0
        )
    )

    ultima_aparicao = memoria.get(
        "ultima_aparicao"
    )

    if score_real > 0:
        bonus *= 1.08

    if vezes >= 8 and score_real == 0:
        bonus *= 0.85

    if 1 <= vezes <= 3 and score_real >= 1:
        bonus *= 1.10

    if ultima_aparicao:

        try:

            ultima = datetime.strptime(
                str(ultima_aparicao),
                "%Y-%m-%d"
            ).date()

            dias = (
                date.today() -
                ultima
            ).days

            if dias <= 2:
                bonus *= 0.95

            elif dias >= 7:
                bonus *= 1.05

        except:
            pass

    return bonus, True


def validar_diversidade_estrutural(
    estrutura,
    memoria,
    estruturas_usadas
):

    hash_estrutura = estrutura[
        "hash_estrutura"
    ]

    score_real = 0
    vezes = 0

    if memoria:

        score_real = float(
            memoria.get(
                "score_medio_real",
                0
            )
        )

        vezes = int(
            memoria.get(
                "vezes_gerado",
                0
            )
        )

    # Estrutura saturada e sem performance
    if vezes >= 5 and score_real < 0.05:

        print(
            f"🚫 Estrutura saturada descartada: "
            f"{hash_estrutura}"
        )

        return False

    # Limite dinâmico
    limite = 1

    if score_real >= 0.25:
        limite = 3

    elif score_real >= 0.05:
        limite = 1

    usadas = estruturas_usadas.get(
        hash_estrutura,
        0
    )

    print(

        f"🧠 Estrutura {hash_estrutura} | "

        f"score={score_real:.4f} | "

        f"vezes={vezes} | "

        f"usadas={usadas} | "

        f"limite={limite}"
    )

    if usadas >= limite:
        return False

    estruturas_usadas[
        hash_estrutura
    ] = usadas + 1

    return True


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(f"🛡️ {VERSAO}")

    fuso = pytz.timezone(
        "America/Sao_Paulo"
    )

    hoje = datetime.now(
        fuso
    ).date().isoformat()

    historico = carregar_historico()

    ultimo_real = historico[-1]["numeros"]

    concurso_ref = int(
        historico[-1]["concurso"]
    ) + 1

    print(
        f"📌 Concurso alvo: "
        f"{concurso_ref}"
    )

    base_scores, _ = (
        calcular_score_combinacoes_reais()
    )

    fator_global = (
        obter_fator_aprendizado_global()
        ["fator"]
    )

    print(
        f"🧠 Fator global: "
        f"{fator_global:.4f}"
    )

    vistos_historico = {

        tuple(
            sorted(
                h["numeros"]
            )
        )

        for h in historico
    }

    candidatos = []
    estruturas_usadas = {}

    pool = list(
        range(1, 26)
    )

    validos = 0

    for _ in range(
        MAX_TENTATIVAS
    ):

        if len(candidatos) >= 5000:
            break

        jogo = sorted(
            random.sample(
                pool,
                15
            )
        )

        if tuple(jogo) in vistos_historico:
            continue

        filtros = calcular_filtros(
            jogo,
            ultimo_real
        )

        if not validar_jogo(
            filtros
        ):
            continue

        estrutura = extrair_estrutura(
            jogo
        )

        memoria = buscar_cenario_similar(
            supabase=supabase,
            estrutura=estrutura
        )

        if not validar_diversidade_estrutural(
            estrutura=estrutura,
            memoria=memoria,
            estruturas_usadas=estruturas_usadas
        ):
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

        mem_bonus, mem_match = (
            calcular_bonus_memoria(
                memoria
            )
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

        (
            validos /
            MAX_TENTATIVAS
        )

        * 3268760
    )

    print(
        f"📊 Universo filtrado: "
        f"{universo_estimado}"
    )

    candidatos.sort(

        key=lambda x:
        x["score"],

        reverse=True
    )

    finais = []

    for cand in candidatos:

        conflito = False

        for existente in finais:

            diff = len(

                set(
                    cand["nums"]
                )

                ^

                set(
                    existente["nums"]
                )
            )

            if diff < 10:

                conflito = True
                break

        if conflito:
            continue

        finais.append(
            cand
        )

        if len(finais) >= QTD_FINAL:
            break

    print("🏆 TOP 7")

    payload = []

    for i, cand in enumerate(
        finais,
        start=1
    ):

        jogo = cand["nums"]

        filtros = cand["filtros"]

        print(

            f"{i}º | "

            f"{cand['score']:.4f} | "

            f"{jogo}"
        )

        payload.append({

            "data_referencia": hoje,

            "concurso_referencia": concurso_ref,

            "indice_palpite": i,

            "tipo": (
                "fixo"
                if i == 1
                else "estatistico"
            ),

            "numeros": json.dumps(
                jogo
            ),

            "pares": filtros["pares"],

            "impares": (
                15 -
                filtros["pares"]
            ),

            "soma_total": filtros["soma"],

            "processado": False,

            "conferido": False,

            "versao_gerador": VERSAO,

            "metricas": {

                "score": round(
                    cand["score"],
                    6
                ),

                "universo_estimado":
                    universo_estimado,

                "memoria_match":
                    cand["memoria_match"],

                "primos":
                    filtros["primos"],

                "moldura":
                    filtros["moldura"]
            }
        })

    supabase.table(
        "palpites_validos"
    ).delete() \
    .eq(
        "concurso_referencia",
        concurso_ref
    ) \
    .execute()

    supabase.table(
        "palpites_validos"
    ).upsert(

        payload,

        on_conflict=(
            "concurso_referencia,"
            "indice_palpite"
        )

    ).execute()

    print(
        f"✅ {VERSAO} concluída"
    )


if __name__ == "__main__":
    main()