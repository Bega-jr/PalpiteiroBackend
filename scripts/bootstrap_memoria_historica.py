import sys
import json
import numpy as np

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "bootstrap-v2.2-feedback-loop"

PRIMOS = {2,3,5,7,11,13,17,19,23}


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
                clean = valor.strip('"').replace("\\", "")
                return [int(x) for x in json.loads(clean)]
            except:
                return []

    return []


def extrair_estrutura(nums):

    linhas_lista = [

        sum(1 for n in nums if 1 <= n <= 5),
        sum(1 for n in nums if 6 <= n <= 10),
        sum(1 for n in nums if 11 <= n <= 15),
        sum(1 for n in nums if 16 <= n <= 20),
        sum(1 for n in nums if 21 <= n <= 25),

    ]

    return {

        "soma_faixa": int(
            round(sum(nums) / 10) * 10
        ),

        "pares": sum(
            1 for n in nums if n % 2 == 0
        ),

        "primos": sum(
            1 for n in nums if n in PRIMOS
        ),

        "linhas": linhas_lista,

        "hash_estrutura": "-".join(
            map(str, linhas_lista)
        )
    }


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        f"🚀 [{VERSAO}] Iniciando Bootstrap de Memória Estrutural"
    )

    historico = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso")
        .execute()
        .data
    )

    print(
        f"📊 Concursos carregados: "
        f"{len(historico)}"
    )

    estruturas = {}
    mapa_resultados = {}

    # ======================================================
    # FASE 1
    # ======================================================
    for row in historico:

        nums = parse_numeros(
            row["dezenas"]
        )

        if not nums:
            continue

        concurso = int(
            row["concurso"]
        )

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

                "vezes_gerado":
                    0
            }

        estruturas[chave][
            "vezes_gerado"
        ] += 1

    payload = []

    agora = datetime.now().isoformat()

    for item in estruturas.values():

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

            "acertos_11": 0,
            "acertos_12": 0,
            "acertos_13": 0,
            "acertos_14": 0,
            "acertos_15": 0,

            "score_medio_real": 0,

            "tendencia": 0,
            "saturacao": 0,

            "updated_at":
                agora
        })

    print(
        f"🧠 Estruturas únicas mapeadas: "
        f"{len(payload)}"
    )

    print("🧹 Limpando memoria_cenarios...")

    (
        supabase
        .table("memoria_cenarios")
        .delete()
        .neq("soma_faixa", -1)
        .execute()
    )

    print("📥 Gravando cenários...")

    for i in range(0, len(payload), 200):

        (
            supabase
            .table("memoria_cenarios")
            .insert(payload[i:i+200])
            .execute()
        )

    print("✅ Fase 1 concluída")

    # ======================================================
    # FASE 2
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

    print(
        f"📊 Palpites encontrados: "
        f"{len(todos_palpites)}"
    )

    palpites_por_concurso = {}

    ignorados = 0

    for p in todos_palpites:

        concurso_ref = p.get(
            "concurso_referencia"
        )

        if not concurso_ref:

            ignorados += 1
            continue

        try:

            cc = int(concurso_ref)

        except:

            ignorados += 1
            continue

        jogo = parse_numeros(
            p.get("numeros")
        )

        if not jogo:

            ignorados += 1
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

    print(
        f"📌 Concursos encontrados nos palpites: "
        f"{len(palpites_por_concurso)}"
    )

    print(
        f"⚠️ Registros ignorados: "
        f"{ignorados}"
    )

    payload_feedback = []

    matches = 0

    for cc, jogos in palpites_por_concurso.items():

        if cc not in mapa_resultados:
            continue

        matches += 1

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
            np.mean(
                acertos_lista
            )
        )

        if media < 9:
            fator = 0.92

        elif media >= 11:
            fator = 1.05

        else:
            fator = 1.00

        payload_feedback.append({

            "concurso_referencia":
                cc,

            "media_acertos_ia":
                round(
                    media,
                    2
                ),

            "fator_correcao":
                fator
        })

    print(
        f"🎯 Matches encontrados: "
        f"{matches}"
    )

    if not payload_feedback:

        print(
            "⚠️ Nenhuma correspondência real encontrada."
        )

        return

    print(
        "🧹 Limpando memoria_feedback_loop..."
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

    print(
        f"📥 Gravando "
        f"{len(payload_feedback)} registros..."
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
