import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


VERSAO = "bootstrap-v1.1"

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
            1 for n in nums
            if n % 2 == 0
        ),

        "primos": sum(
            1 for n in nums
            if n in PRIMOS
        ),

        "linhas": json.dumps(
            linhas_lista
        ),

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
        f"🚀 [{VERSAO}] Bootstrap memória estrutural"
    )

    historico = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso"
    ).execute().data

    print(
        f"📊 Concursos carregados: "
        f"{len(historico)}"
    )

    estruturas = {}

    for row in historico:

        nums = parse_numeros(
            row["dezenas"]
        )

        if not nums:
            continue

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

            # compatibilidade com schema atual
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
        f"🧠 Estruturas únicas: "
        f"{len(payload)}"
    )

    supabase.table(
        "memoria_cenarios"
    ).upsert(
        payload,
        on_conflict=(
            "soma_faixa,"
            "pares,"
            "primos,"
            "hash_estrutura"
        )
    ).execute()

    print(
        "✅ Bootstrap concluído"
    )


if __name__ == "__main__":
    main()