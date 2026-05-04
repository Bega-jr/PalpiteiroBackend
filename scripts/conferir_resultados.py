import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


def extrair_estrutura(nums):

    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(n % 2 == 0 for n in nums),
        "primos": sum(
            1 for n in nums
            if n in {2,3,5,7,11,13,17,19,23}
        ),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }


def peso_acerto(acertos):

    pesos = {
        11: 1,
        12: 2,
        13: 5,
        14: 20,
        15: 100
    }

    return pesos.get(acertos, 0)


def parse_numeros(valor):

    if isinstance(valor, list):
        return valor

    if isinstance(valor, str):
        return json.loads(valor)

    return None


def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not concursos:
        return

    concurso_atual = concursos[0]["concurso"]

    dezenas = set(
        map(int, concursos[0]["dezenas"])
    )

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .execute()
        .data
    )

    palpites = [
        p for p in palpites
        if p["concurso_referencia"] < concurso_atual
    ]

    print(f"📌 {len(palpites)} palpites")

    for p in palpites:

        numeros = parse_numeros(
            p["numeros"]
        )

        nums = set(
            map(int, numeros)
        )

        acertos = len(
            nums & dezenas
        )

        estrutura = extrair_estrutura(
            list(nums)
        )

        peso = peso_acerto(
            acertos
        )

        (
            supabase
            .table("palpites_validos")
            .update({
                "acertos": acertos
            })
            .eq("id", p["id"])
            .execute()
        )

        existente = (
            supabase
            .table("memoria_cenarios")
            .select("*")
            .eq("soma_faixa", estrutura["soma_faixa"])
            .eq("pares", estrutura["pares"])
            .eq("primos", estrutura["primos"])
            .execute()
        )

        registro = (
            existente.data[0]
            if existente.data
            else {}
        )

        vezes = int(
            registro.get(
                "vezes_gerado",
                0
            )
        ) + 1

        hits = int(
            registro.get(
                f"acertos_{acertos}",
                0
            )
        ) + 1

        payload = {
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "vezes_gerado": vezes,
            f"acertos_{acertos}": hits,
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        (
            supabase
            .table("memoria_cenarios")
            .upsert(
                payload,
                on_conflict="soma_faixa,pares,primos,linhas"
            )
            .execute()
        )

    print("✅ Conferência concluída")


if __name__ == "__main__":
    main()
