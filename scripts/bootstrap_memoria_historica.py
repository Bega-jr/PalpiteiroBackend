import sys
import json
import math
import numpy as np

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "bootstrap-v2.4-macro-recencia"

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}


# ======================================================
# AUX
# ======================================================
def parse_numeros(valor):

    if not valor:
        return []

    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):

        try:
            return [int(x) for x in json.loads(valor)]

        except:

            try:

                clean = (
                    valor
                    .strip('"')
                    .replace("\\", "")
                )

                return [
                    int(x)
                    for x in json.loads(clean)
                ]

            except:
                return []

    return []


def normalizar_concurso(valor):

    if valor is None:
        return None

    try:
        return int(float(valor))
    except:
        return None


def calcular_macro_dispersao(nums):

    return [

        sum(1 for n in nums if 1 <= n <= 8),
        sum(1 for n in nums if 9 <= n <= 17),
        sum(1 for n in nums if 18 <= n <= 25)

    ]


def extrair_estrutura(nums):

    linhas_lista = [

        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25)

    ]

    macro_lista = calcular_macro_dispersao(
        nums
    )

    return {

        "soma_faixa":
            int(
                round(sum(nums) / 10) * 10
            ),

        "pares":
            sum(
                1 for n in nums
                if n % 2 == 0
            ),

        "primos":
            sum(
                1 for n in nums
                if n in PRIMOS
            ),

        "linhas":
            linhas_lista,

        "macro":
            macro_lista,

        "hash_estrutura":
            "-".join(
                map(str, linhas_lista)
            ),

        "hash_macro":
            "-".join(
                map(str, macro_lista)
            )
    }


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        f"🚀 [{VERSAO}] Iniciando Bootstrap"
    )

    historico = (

        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order(
            "concurso",
            desc=True
        )
        .execute()
        .data

    )

    print(
        f"📊 Concursos carregados: "
        f"{len(historico)}"
    )

    estruturas = {}
    mapa_resultados = {}

    concursos_ordenados = []

    for row in historico:

        concurso = normalizar_concurso(
            row.get("concurso")
        )

        if concurso is None:
            continue

        concursos_ordenados.append(
            concurso
        )

        nums = parse_numeros(
            row.get("dezenas")
        )

        if not nums:
            continue

        mapa_resultados[
            concurso
        ] = set(nums)

        estrutura = extrair_estrutura(
            nums
        )

        chave = (

            estrutura["soma_faixa"],
            estrutura["pares"],
            estrutura["primos"],
            estrutura["hash_estrutura"]

        )

        if chave not in estruturas:

            estruturas[chave] = {

                "soma_faixa":
                    estrutura["soma_faixa"],

                "pares":
                    estrutura["pares"],

                "primos":
                    estrutura["primos"],

                "linhas":
                    estrutura["linhas"],

                "hash_estrutura":
                    estrutura["hash_estrutura"],

                "macro":
                    estrutura["macro"],

                "hash_macro":
                    estrutura["hash_macro"],

                "vezes_gerado":
                    0
            }

        estruturas[
            chave
        ]["vezes_gerado"] += 1

    agora = datetime.now().isoformat()

    payload = []

    for item in estruturas.values():

        saturacao = round(
            math.log(
                item["vezes_gerado"] + 1
            ),
            4
        )

        payload.append({

            "soma_faixa":
                item["soma_faixa"],

            "pares":
                item["pares"],

            "primos":
                item["primos"],

            "linhas":
                item["linhas"],

            "hash_estrutura":
                item["hash_estrutura"],

            "vezes_gerado":
                item["vezes_gerado"],

            # backward compatible
            "acertos_11": 0,
            "acertos_12": 0,
            "acertos_13": 0,
            "acertos_14": 0,
            "acertos_15": 0,

            "score_medio_real": 0,

            "tendencia": 0,

            "saturacao":
                saturacao,

            "updated_at":
                agora
        })

    print(
        f"🧠 Estruturas únicas: "
        f"{len(payload)}"
    )

    print(
        "🧹 Limpando memoria_cenarios..."
    )

    (
        supabase
        .table("memoria_cenarios")
        .delete()
        .neq("soma_faixa", -1)
        .execute()
    )

    print(
        "📥 Gravando cenários..."
    )

    for i in range(0, len(payload), 200):

        (
            supabase
            .table("memoria_cenarios")
            .insert(payload[i:i+200])
            .execute()
        )

    print(
        "✅ Fase 1 concluída"
    )

    # ======================================================
    # FEEDBACK LOOP
    # ======================================================
    print(
        "\n🔄 Iniciando feedback loop..."
    )

    todos_palpites = (

        supabase
        .table("palpites_validos")
        .select(
            "concurso_referencia,numeros"
        )
        .execute()
        .data

    )

    if not todos_palpites:

        print(
            "⚠️ Nenhum palpite encontrado."
        )

        return

    palpites_por_concurso = {}

    for p in todos_palpites:

        cc = normalizar_concurso(
            p.get("concurso_referencia")
        )

        if cc is None:
            continue

        jogo = parse_numeros(
            p.get("numeros")
        )

        if not jogo:
            continue

        if cc not in palpites_por_concurso:

            palpites_por_concurso[
                cc
            ] = []

        palpites_por_concurso[
            cc
        ].append(
            jogo
        )

    payload_feedback = []

    for idx, (cc, jogos) in enumerate(
        palpites_por_concurso.items()
    ):

        if cc not in mapa_resultados:
            continue

        resultado_real = mapa_resultados[
            cc
        ]

        acertos_lista = []

        for jogo in jogos:

            acertos = len(
                set(jogo) &
                resultado_real
            )

            acertos_lista.append(
                acertos
            )

        media = float(
            np.mean(acertos_lista)
        )

        peso_recencia = max(
            0.85,
            1 - (idx * 0.01)
        )

        media_ajustada = (
            media *
            peso_recencia
        )

        if media_ajustada < 9:
            fator = 0.92

        elif media_ajustada >= 11:
            fator = 1.05

        else:
            fator = 1.00

        payload_feedback.append({

            "concurso_referencia":
                cc,

            "media_acertos_ia":
                round(
                    media_ajustada,
                    2
                ),

            "fator_correcao":
                fator
        })

    print(
        f"📥 Gravando "
        f"{len(payload_feedback)} registros..."
    )

    (
        supabase
        .table("memoria_feedback_loop")
        .delete()
        .neq(
            "concurso_referencia",
            -1
        )
        .execute()
    )

    for i in range(
        0,
        len(payload_feedback),
        200
    ):

        (
            supabase
            .table("memoria_feedback_loop")
            .insert(
                payload_feedback[i:i+200]
            )
            .execute()
        )

    print(
        "✅ Fase 2 concluída"
    )


if __name__ == "__main__":
    main()
