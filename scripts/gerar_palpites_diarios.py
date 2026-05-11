import sys
import json
import random
import numpy as np
import pytz

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

from app.services.aprendizado_service_v3 import (
    obter_fator_aprendizado_global
)

from app.services.estatisticas_combinacao_v3 import (
    calcular_score_combinacoes_reais
)

from scripts.processamento_diario_lotofacil import (
    carregar_historico,
    extrair_estrutura,
    buscar_cenario_similar
)


VERSAO = "v13.6-pro-memory-dynamic"

QTD_FINAL = 7

MAX_TENTATIVAS = 100000

NUMEROS_PRIMOS = {
    2, 3, 5, 7, 11, 13, 17, 19, 23
}

MOLDURA = {
    1, 2, 3, 4, 5,
    6, 10, 11, 15,
    16, 20, 21,
    22, 23, 24, 25
}


# ======================================================
# FILTROS
# ======================================================

def calcular_filtros_pro(
    nums,
    ultimo_concurso
):

    pares = sum(
        1 for n in nums
        if n % 2 == 0
    )

    soma = sum(nums)

    primos = sum(
        1 for n in nums
        if n in NUMEROS_PRIMOS
    )

    moldura = sum(
        1 for n in nums
        if n in MOLDURA
    )

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

        "soma": soma,

        "primos": primos,

        "moldura": moldura,

        "repetidos": repetidos,

        "seq_max": seq_max
    }


def validar_jogo_pro(
    filtros
):

    if not (
        165 <= filtros["soma"] <= 210
    ):
        return False

    if not (
        6 <= filtros["pares"] <= 9
    ):
        return False

    if not (
        4 <= filtros["primos"] <= 7
    ):
        return False

    if not (
        8 <= filtros["moldura"] <= 12
    ):
        return False

    if not (
        8 <= filtros["repetidos"] <= 10
    ):
        return False

    if filtros["seq_max"] > 4:
        return False

    return True


# ======================================================
# MEMÓRIA
# ======================================================

def calcular_bonus_memoria(
    memoria
):

    if not memoria:
        return 1.0

    score_real = float(
        memoria.get(
            "score_medio_real",
            0
        )
    )

    if score_real >= 5:
        return 1.25

    elif score_real >= 2:
        return 1.15

    elif score_real > 0:
        return 1.05

    return 1.0


# ======================================================
# MAIN
# ======================================================

def main():

    supabase = get_supabase()

    fuso = pytz.timezone(
        "America/Sao_Paulo"
    )

    hoje = datetime.now(
        fuso
    ).date().isoformat()

    print(
        f"🛡️ {VERSAO}"
    )

    historico = carregar_historico()

    ultimo_real = historico[-1][
        "numeros"
    ]

    concurso_ref = int(
        historico[-1]["concurso"]
    ) + 1

    print(
        f"📌 Concurso alvo: "
        f"{concurso_ref}"
    )

    # IA BASE
    base_scores, _ = calcular_score_combinacoes_reais()

    fator_global = float(
        obter_fator_aprendizado_global()[
            "fator"
        ]
    )

    print(
        f"🧠 Fator global: "
        f"{fator_global:.4f}"
    )

    candidatos = []

    vistos_historico = set(
        tuple(
            sorted(
                h["numeros"]
            )
        )
        for h in historico
    )

    pool = list(
        range(1, 26)
    )

    validos = 0

    print(
        "🎯 Gerando candidatos..."
    )

    for _ in range(
        MAX_TENTATIVAS
    ):

        if len(
            candidatos
        ) >= 5000:
            break

        jogo = sorted(
            random.sample(
                pool,
                15
            )
        )

        # Anti-plágio
        if tuple(jogo) in vistos_historico:
            continue

        filtros = calcular_filtros_pro(
            jogo,
            ultimo_real
        )

        # Filtros
        if not validar_jogo_pro(
            filtros
        ):
            continue

        validos += 1

        # Score base
        score_base = float(
            np.mean([
                base_scores.get(
                    tuple([n]),
                    0.5
                )
                for n in jogo
            ])
        )

        # Memória
        estrutura = extrair_estrutura(
            jogo
        )

        memoria = buscar_cenario_similar(
            supabase,
            estrutura
        )

        bonus_memoria = calcular_bonus_memoria(
            memoria
        )

        score_final = (

            score_base *

            bonus_memoria *

            fator_global
        )

        candidatos.append({

            "nums": jogo,

            "score": score_final,

            "filtros": filtros,

            "memoria_match": (
                bonus_memoria > 1
            )
        })

    universo_estimado = int(
        (
            validos /
            MAX_TENTATIVAS
        ) * 3268760
    )

    print(
        f"📊 Universo filtrado: "
        f"{universo_estimado}"
    )

    # Ranking
    candidatos.sort(
        key=lambda x:
        x["score"],
        reverse=True
    )

    finais = []

    for candidato in candidatos:

        # Diversidade mínima
        if any(

            len(
                set(
                    candidato["nums"]
                ) ^
                set(
                    f["nums"]
                )
            ) < 10

            for f in finais
        ):
            continue

        finais.append(
            candidato
        )

        if len(
            finais
        ) >= QTD_FINAL:
            break

    if not finais:

        raise Exception(
            "Nenhum candidato válido gerado."
        )

    # Persistência
    payload = []

    print(
        f"\n🏆 TOP "
        f"{len(finais)}"
    )

    for i, item in enumerate(
        finais,
        start=1
    ):

        nums = item["nums"]

        filtros = item[
            "filtros"
        ]

        print(
            f"{i}º | "
            f"{item['score']:.4f} | "
            f"{nums}"
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
                nums
            ),

            "pares": filtros[
                "pares"
            ],

            "impares": (
                15 -
                filtros["pares"]
            ),

            "soma_total": filtros[
                "soma"
            ],

            "processado": False,

            "conferido": False,

            "versao_gerador": VERSAO,

            "metricas": {

                "score": round(
                    item["score"],
                    6
                ),

                "universo_estimado": universo_estimado,

                "memoria_match": item[
                    "memoria_match"
                ],

                "primos": filtros[
                    "primos"
                ],

                "moldura": filtros[
                    "moldura"
                ]
            }
        })

    supabase.table(
        "palpites_validos"
    ).upsert(
        payload,
        on_conflict="data_referencia,indice_palpite"
    ).execute()

    print(
        f"\n✅ {VERSAO} concluída"
    )


if __name__ == "__main__":
    main()


