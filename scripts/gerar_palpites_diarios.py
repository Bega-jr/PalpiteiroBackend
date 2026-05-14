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

# ======================================================
# CONFIG
# ======================================================
VERSAO = "v16.2-adaptive-memory-structural"

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
def media_segura(v, fallback=0.5):

    validos = [x for x in v if x is not None]

    if not validos:
        return fallback

    return float(np.mean(validos))


def calcular_filtros(nums, ultimo):

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
        set(nums) & set(ultimo)
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


# ======================================================
# VALIDAÇÃO
# ======================================================
def validar_autonomo(
    filtros,
    linhas,
    limites
):

    return (

        limites["soma_min"]
        <= filtros["soma"]
        <= limites["soma_max"]

        and

        limites["pares_min"]
        <= filtros["pares"]
        <= limites["pares_max"]

        and

        limites["primos_min"]
        <= filtros["primos"]
        <= limites["primos_max"]

        and

        limites["moldura_min"]
        <= filtros["moldura"]
        <= limites["moldura_max"]

        and

        limites["repetidos_min"]
        <= filtros["repetidos"]
        <= limites["repetidos_max"]

        and

        filtros["seq_max"]
        <= limites["seq_max_limite"]

        and

        max(linhas)
        <= limites["max_linha_limite"]
    )


# ======================================================
# SCORE
# ======================================================
def score(jogo, base):

    s1 = media_segura([
        base.get((n,), 0.5)
        for n in jogo
    ])

    s2 = media_segura([

        base.get(
            tuple(sorted(p)),
            0.5
        )

        for p in itertools.combinations(
            jogo,
            2
        )
    ])

    ternos = list(
        itertools.combinations(
            jogo,
            3
        )
    )

    random.shuffle(ternos)

    ternos_amostrados = ternos[:120]

    scores_ternos = [

        base.get(
            tuple(sorted(t)),
            0.5
        )

        for t in ternos_amostrados
    ]

    s3 = (

        media_segura(
            scores_ternos
        ) * 0.70

        +

        max(scores_ternos) * 0.30
    )

    noise = random.uniform(
        0.97,
        1.03
    )

    return (

        (
            (s1 * 0.25)
            +
            (s2 * 0.35)
            +
            (s3 * 0.40)
        )

        * noise
    )


# ======================================================
# BONUS
# ======================================================
def bonus_moldura(
    estrutura,
    memoria
):

    if not memoria:
        return 1.0

    linhas = estrutura["linhas"]

    vezes = int(
        memoria.get(
            "vezes_gerado",
            0
        )
    )

    score_real = float(
        memoria.get(
            "score_medio_real",
            0
        )
    )

    if max(linhas) >= 10:
        return 0.90

    if 2 <= max(linhas) <= 5:
        return 1.08

    if vezes <= 2:
        return 1.05

    if score_real >= 3:
        return 1.02

    return 1.0


# ======================================================
# NOVO BONUS ESTRUTURAL
# ======================================================
def bonus_estrutura(mem):

    if not mem:
        return 1.01

    vezes = int(
        mem.get(
            "vezes_gerado",
            0
        )
    )

    score_real = float(
        mem.get(
            "score_medio_real",
            0
        )
    )

    if vezes >= 40:
        return 0.97

    if vezes <= 5 and score_real >= 1:
        return 1.04

    if vezes <= 5:
        return 1.02

    if 6 <= vezes <= 20:
        return 1.01

    return 1.0


# ======================================================
# DIVERSIDADE
# ======================================================
def diversidade_ok(
    novo,
    lista
):

    return all(

        len(
            set(novo)
            ^
            set(x["nums"])
        ) >= 8

        for x in lista
    )


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

    hist = carregar_historico()

    ultimo = hist[-1]["numeros"]

    concurso_ref = int(
        hist[-1]["concurso"]
    ) + 1

    base_scores, _ = (
        calcular_score_combinacoes_reais()
    )

    fator_global = (
        obter_fator_aprendizado_global()["fator"]
    )

    # ==================================================
    # FEEDBACK LOOP
    # ==================================================
    fator_feedback_loop = 1.0

    try:

        concurso_anterior = (
            concurso_ref - 1
        )

        rows = (

            supabase
            .table(
                "memoria_feedback_loop"
            )
            .select(
                "fator_correcao"
            )
            .eq(
                "concurso_referencia",
                concurso_anterior
            )
            .execute()
            .data
        )

        if rows:

            fator_feedback_loop = float(
                rows[0][
                    "fator_correcao"
                ]
            )

        fator_feedback_loop = max(
            0.97,
            min(
                1.03,
                fator_feedback_loop
            )
        )

        print(
            f"🎛️ Feedback Médio: {fator_feedback_loop}"
        )

    except:

        fator_feedback_loop = 1.0


    # ==================================================
    # LIMITES DINÂMICOS
    # ==================================================
    janela = hist[-25:]

    somas = []
    pares = []
    primos = []
    molduras = []
    repetidos = []
    seqs = []
    linhas = []

    for i, h in enumerate(janela):

        nums = h["numeros"]

        ref_ant = (
            janela[i - 1]["numeros"]
            if i > 0
            else nums
        )

        filtros = calcular_filtros(
            nums,
            ref_ant
        )

        estrutura = extrair_estrutura(
            nums
        )

        somas.append(
            filtros["soma"]
        )

        pares.append(
            filtros["pares"]
        )

        primos.append(
            filtros["primos"]
        )

        molduras.append(
            filtros["moldura"]
        )

        repetidos.append(
            filtros["repetidos"]
        )

        seqs.append(
            filtros["seq_max"]
        )

        linhas.append(
            max(
                estrutura["linhas"]
            )
        )

    limites = {

        "soma_min":
            int(
                np.percentile(
                    somas,
                    10
                )
            ),

        "soma_max":
            int(
                np.percentile(
                    somas,
                    90
                )
            ),

        "pares_min":
            min(pares),

        "pares_max":
            max(pares),

        "primos_min":
            min(primos),

        "primos_max":
            max(primos),

        "moldura_min":
            min(molduras),

        "moldura_max":
            max(molduras),

        "repetidos_min":
            min(repetidos),

        "repetidos_max":
            max(repetidos),

        "seq_max_limite":
            max(seqs),

        "max_linha_limite":
            max(linhas)
    }

    memoria = {

        m["hash_estrutura"]: m

        for m in (

            supabase
            .table(
                "memoria_cenarios"
            )
            .select("*")
            .execute()
            .data
        )
    }

    usados = set(

        tuple(
            sorted(
                h["numeros"]
            )
        )

        for h in hist
    )

    candidatos = []

    pool = list(
        range(1, 26)
    )

    for _ in range(
        MAX_TENTATIVAS
    ):

        if len(
            candidatos
        ) >= 1500:

            break

        jogo = sorted(
            random.sample(
                pool,
                15
            )
        )

        if tuple(
            jogo
        ) in usados:

            continue

        filtros = (
            calcular_filtros(
                jogo,
                ultimo
            )
        )

        estrutura = (
            extrair_estrutura(
                jogo
            )
        )

        mem = memoria.get(
            estrutura[
                "hash_estrutura"
            ]
        )

        if not validar_autonomo(
            filtros,
            estrutura["linhas"],
            limites
        ):
            continue

        if not diversidade_ok(
            jogo,
            candidatos[-25:]
        ):
            continue

        s = score(
            jogo,
            base_scores
        )

        s *= fator_global
        s *= fator_feedback_loop

        s *= bonus_moldura(
            estrutura,
            mem
        )

        s *= bonus_estrutura(
            mem
        )

        candidatos.append({

            "nums": jogo,

            "score": s,

            "filtros": filtros
        })

    candidatos.sort(

        key=lambda x: x["score"],

        reverse=True
    )

    finais = []

    for c in candidatos:

        if len(
            finais
        ) >= QTD_FINAL:

            break

        if diversidade_ok(
            c["nums"],
            finais
        ):

            finais.append(
                c
            )

    print("\n🏆 TOP 7")

    payload = []

    telegram = []

    for i, c in enumerate(
        finais,
        1
    ):

        linha = (
            f"{i}º | "
            f"{c['score']:.6f} | "
            f"{c['nums']}"
        )

        print(
            linha
        )

        telegram.append(
            linha
        )

        payload.append({

            "data_referencia":
                hoje,

            "concurso_referencia":
                concurso_ref,

            "indice_palpite":
                i,

            "tipo":
                "fixo"
                if i == 1
                else "estatistico",

            "numeros":
                json.dumps(
                    c["nums"]
                ),

            "pares":
                c["filtros"][
                    "pares"
                ],

            "impares":
                15
                -
                c["filtros"][
                    "pares"
                ],

            "soma_total":
                c["filtros"][
                    "soma"
                ],

            "processado":
                False,

            "conferido":
                False,

            "versao_gerador":
                VERSAO,

            "metricas": {

                "score":
                    round(
                        c["score"],
                        6
                    ),

                "primos":
                    c["filtros"][
                        "primos"
                    ],

                "moldura":
                    c["filtros"][
                        "moldura"
                    ]
            }
        })

    (
        supabase
        .table(
            "palpites_validos"
        )
        .delete()
        .eq(
            "concurso_referencia",
            concurso_ref
        )
        .execute()
    )

    (
        supabase
        .table(
            "palpites_validos"
        )
        .upsert(
            payload,
            on_conflict="concurso_referencia,indice_palpite"
        )
        .execute()
    )

    print(
        "\n📲 TELEGRAM_PAYLOAD_START"
    )

    print(
        "\n".join(
            telegram
        )
    )

    print(
        "📲 TELEGRAM_PAYLOAD_END"
    )


if __name__ == "__main__":
    main()
