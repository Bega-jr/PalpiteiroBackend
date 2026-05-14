import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "v14.4-conferencia-estavel"

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
            return []

    return []


def extrair_estrutura(nums):

    linhas = [

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
            1 for n in nums
            if n % 2 == 0
        ),

        "primos": sum(
            1 for n in nums
            if n in PRIMOS
        ),

        "hash_estrutura": "-".join(
            map(str, linhas)
        )
    }


# ======================================================
# BOOTSTRAP HISTORICO
# ======================================================
def bootstrap_estrutura_historica(
    supabase,
    estrutura
):

    historico = supabase.table(
        "lotofacil_concursos"
    ).select(
        "dezenas"
    ).execute().data

    freq = 0

    for row in historico:

        nums = parse_numeros(
            row["dezenas"]
        )

        if not nums:
            continue

        e = extrair_estrutura(
            nums
        )

        if (

            e["hash_estrutura"] ==
            estrutura["hash_estrutura"]

        ):

            freq += 1

    supabase.table(
        "memoria_cenarios"
    ).insert({

        "soma_faixa":
            estrutura["soma_faixa"],

        "pares":
            estrutura["pares"],

        "primos":
            estrutura["primos"],

        "hash_estrutura":
            estrutura["hash_estrutura"],

        "vezes_gerado":
            max(freq, 1),

        "score_medio_real":
            0,

        "created_at":
            datetime.now().isoformat(),

        "updated_at":
            datetime.now().isoformat()

    }).execute()

    print(
        f"🧠 Bootstrap criado: "
        f"{estrutura['hash_estrutura']} "
        f"| freq histórica={freq}"
    )


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
         "hash_estrutura",
         estrutura["hash_estrutura"]
     ) \
     .execute()

    if not row.data:

        bootstrap_estrutura_historica(
            supabase,
            estrutura
        )

        row = supabase.table(
            "memoria_cenarios"
        ).select("*") \
         .eq(
             "hash_estrutura",
             estrutura["hash_estrutura"]
         ) \
         .execute()

    mem = row.data[0]

    peso = {
        11: 1,
        12: 2,
        13: 5,
        14: 10,
        15: 15
    }.get(acertos, 0)

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
        (score_antigo * vezes) + peso
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

    supabase.table(
        "memoria_cenarios"
    ).update(
        update
    ).eq(
        "id",
        mem["id"]
    ).execute()


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print(
        f"🏁 [{VERSAO}] Conferência + Bootstrap"
    )

    oficiais = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).execute().data

    mapa = {
        int(r["concurso"]): set(
            parse_numeros(
                r["dezenas"]
            )
        )
        for r in oficiais
    }

    # 🛠️ AJUSTE DE CONTROLE: Busca por conferido=False em vez de processado=False
    pendentes = supabase.table("palpites_validos").select("*") \
     .eq(
         "conferido",
         False
     ) \
     .execute().data

    print(
        f"📌 {len(pendentes)} palpites pendentes"
    )

    processados = 0

    for p in pendentes:

        concurso = int(
            p["concurso_referencia"]
        )

        if concurso not in mapa:

            print(
                f"⏳ Concurso "
                f"{concurso} "
                f"ainda sem resultado oficial"
            )

            continue

        numeros = parse_numeros(
            p["numeros"]
        )

        acertos = len(
            set(numeros) &
            mapa[concurso]
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

        print(
            f"✅ Concurso "
            f"{concurso} | "
            f"Palpite #{p['indice_palpite']} | "
            f"{acertos} acertos"
        )

        processados += 1

    print(
        f"✅ Processo concluído: "
        f"{processados} palpites processados"
    )


if __name__ == "__main__":
    main()

