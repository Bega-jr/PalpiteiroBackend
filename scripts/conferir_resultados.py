import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


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
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in PRIMOS),
        "hash_estrutura": "-".join(map(str, linhas))
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
        "vezes_gerado": novo_total,

        "score_medio_real": round(
            novo_score,
            4
        ),

        "ultima_aparicao": datetime.now().date().isoformat(),

        "updated_at": datetime.now().isoformat()
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
        "vezes_gerado": novo_total,

        "score_medio_real": round(
            novo_score,
            4
        ),

        "updated_at": datetime.now().isoformat()
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
        int(r["concurso"]): set(
            parse_numeros(
                r["dezenas"]
            )
        )
        for r in oficiais
    }

    pendentes = supabase.table(
        "palpites_validos"
    ).select(
        "*"
    ).eq(
        "processado",
        False
    ).execute().data

    print(
        f"📌 {len(pendentes)} palpites pendentes"
    )

    for p in pendentes:

        concurso = int(
            p["concurso_referencia"]
        )

        if concurso not in mapa:
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
            "acertos": acertos,
            "processado": True,
            "conferido": True
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

    print("✅ Processo concluído")


if __name__ == "__main__":
    main()
