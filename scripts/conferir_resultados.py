import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


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
            return [
                int(x)
                for x in json.loads(valor)
            ]
        except:
            return []

    return []


def extrair_estrutura(nums):

    linhas = [

        sum(
            1 for n in nums
            if 1 <= n <= 5
        ),

        sum(
            1 for n in nums
            if 6 <= n <= 10
        ),

        sum(
            1 for n in nums
            if 11 <= n <= 15
        ),

        sum(
            1 for n in nums
            if 16 <= n <= 20
        ),

        sum(
            1 for n in nums
            if 21 <= n <= 25
        ),
    ]

    return {

        "soma_faixa":
            int(
                round(
                    sum(nums) / 10
                ) * 10
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

        "hash_estrutura":
            "-".join(
                map(str, linhas)
            )
    }


# ======================================================
# MEMORIA ESTRUTURAL
# ======================================================
def atualizar_memoria_estrutural(
    supabase,
    palpite,
    acertos
):

    numeros = parse_numeros(
        palpite["numeros"]
    )

    if not numeros:
        return

    estrutura = extrair_estrutura(
        numeros
    )

    row = supabase.table(
        "memoria_cenarios"
    ).select("*") \
     .eq(
         "soma_faixa",
         estrutura["soma_faixa"]
     ) \
     .eq(
         "pares",
         estrutura["pares"]
     ) \
     .eq(
         "primos",
         estrutura["primos"]
     ) \
     .eq(
         "hash_estrutura",
         estrutura["hash_estrutura"]
     ) \
     .execute()

    if not row.data:
        return

    mem = row.data[0]

    peso = {
        11: 1,
        12: 2,
        13: 5,
        14: 10,
        15: 15
    }.get(
        acertos,
        0
    )

    vezes = int(
        mem.get(
            "vezes_gerado",
            0
        )
    )

    score_antigo = float(
        mem.get(
            "score_medio_real",
            0
        )
    )

    novo_total = vezes + 1

    novo_score = (
        (
            score_antigo * vezes
        ) + peso
    ) / novo_total

    update = {

        "vezes_gerado":
            novo_total,

        "score_medio_real":
            round(
                novo_score,
                4
            ),

        "ultima_aparicao":
            datetime.now().date().isoformat(),

        "updated_at":
            datetime.now().isoformat()
    }

    if acertos >= 11:

        coluna = f"acertos_{acertos}"

        update[coluna] = int(
            mem.get(
                coluna,
                0
            )
        ) + 1

    supabase.table(
        "memoria_cenarios"
    ).update(
        update
    ).eq(
        "id",
        mem["id"]
    ).execute()


# ======================================================
# MEMORIA POSICIONAL
# ======================================================
def atualizar_memoria_posicional(
    supabase,
    indice_palpite,
    acertos
):

    row = supabase.table(
        "memoria_posicional"
    ).select("*") \
     .eq(
         "indice_palpite",
         indice_palpite
     ) \
     .execute()

    if not row.data:
        return

    mem = row.data[0]

    peso = {
        11: 1,
        12: 2,
        13: 5,
        14: 10,
        15: 15
    }.get(
        acertos,
        0
    )

    vezes = int(
        mem.get(
            "vezes_gerado",
            0
        )
    )

    score_antigo = float(
        mem.get(
            "score_medio_real",
            0
        )
    )

    novo_total = vezes + 1

    novo_score = (
        (
            score_antigo * vezes
        ) + peso
    ) / novo_total

    update = {

        "vezes_gerado":
            novo_total,

        "score_medio_real":
            round(
                novo_score,
                4
            ),

        "updated_at":
            datetime.now().isoformat()
    }

    if acertos >= 11:

        coluna = f"acertos_{acertos}"

        update[coluna] = int(
            mem.get(
                coluna,
                0
            )
        ) + 1

    supabase.table(
        "memoria_posicional"
    ).update(
        update
    ).eq(
        "indice_palpite",
        indice_palpite
    ).execute()


# ======================================================
# RESULTADO REAL
# ======================================================
def salvar_resultado_real(
    supabase,
    concurso
):

    registros = supabase.table(
        "palpites_validos"
    ).select("*") \
     .eq(
         "concurso_referencia",
         concurso
     ) \
     .execute().data

    if not registros:
        return

    grupos = {}

    for r in registros:

        chave = (
            r.get(
                "versao_gerador"
            ),
            r.get(
                "tipo"
            )
        )

        grupos.setdefault(
            chave,
            []
        ).append(r)

    for (
        versao,
        tipo
    ), itens in grupos.items():

        qtd = len(itens)

        contadores = {
            11: 0,
            12: 0,
            13: 0,
            14: 0,
            15: 0
        }

        score_total = 0

        for item in itens:

            acertos = int(
                item.get(
                    "acertos",
                    0
                )
            )

            if acertos >= 11:

                contadores[
                    acertos
                ] += 1

            peso = {
                11: 1,
                12: 2,
                13: 5,
                14: 10,
                15: 15
            }.get(
                acertos,
                0
            )

            score_total += peso

        score_medio = round(
            score_total / qtd,
            4
        )

        eficiencia = round(
            (
                sum(
                    contadores.values()
                ) / qtd
            ) * 100,
            2
        )

        payload = {

            "data_referencia":
                datetime.now().date().isoformat(),

            "concurso_inicio":
                concurso,

            "concurso_fim":
                concurso,

            "tipo_palpite":
                tipo,

            "versao_gerador":
                versao,

            "qtd_palpites":
                qtd,

            "acertos_11":
                contadores[11],

            "acertos_12":
                contadores[12],

            "acertos_13":
                contadores[13],

            "acertos_14":
                contadores[14],

            "acertos_15":
                contadores[15],

            "total_concursos":
                1,

            "score_ponderado":
                score_total,

            "score_medio":
                score_medio,

            "eficiencia":
                eficiencia,

            "taxa_12":
                round(
                    (
                        contadores[12] / qtd
                    ) * 100,
                    2
                ),

            "taxa_13":
                round(
                    (
                        contadores[13] / qtd
                    ) * 100,
                    2
                ),

            "taxa_14":
                round(
                    (
                        contadores[14] / qtd
                    ) * 100,
                    2
                ),

            "taxa_15":
                round(
                    (
                        contadores[15] / qtd
                    ) * 100,
                    2
                )
        }

        supabase.table(
            "palpites_resultados_reais"
        ).upsert(
            payload,
            on_conflict=(
                "concurso_inicio,"
                "versao_gerador,"
                "tipo_palpite"
            )
        ).execute()


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        "🏁 [v14.0] Conferência + Memória Posicional"
    )

    oficiais = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso",
        desc=True
    ).limit(
        500
    ).execute().data

    mapa = {

        int(
            r["concurso"]
        ): set(
            parse_numeros(
                r["dezenas"]
            )
        )

        for r in oficiais
    }

    pendentes = supabase.table(
        "palpites_validos"
    ).select("*") \
     .eq(
         "processado",
         False
     ) \
     .execute().data

    print(
        f"📌 {len(pendentes)} palpites pendentes"
    )

    concursos_processados = set()

    for p in pendentes:

        concurso = int(
            p["concurso_referencia"]
        )

        if concurso not in mapa:
            continue

        concursos_processados.add(
            concurso
        )

        numeros = parse_numeros(
            p["numeros"]
        )

        acertos = len(

            set(
                numeros
            ) &

            mapa[
                concurso
            ]
        )

        supabase.table(
            "palpites_validos"
        ).update({

            "acertos":
                acertos,

            "processado":
                True,

            "conferido":
                True

        }).eq(
            "id",
            p["id"]
        ).execute()

        atualizar_memoria_estrutural(
            supabase,
            p,
            acertos
        )

        atualizar_memoria_posicional(
            supabase,
            int(
                p["indice_palpite"]
            ),
            acertos
        )

    for concurso in concursos_processados:

        salvar_resultado_real(
            supabase,
            concurso
        )

    print(
        "✅ Processo concluído"
    )


if __name__ == "__main__":
    main()
