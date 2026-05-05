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
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(
            1 for n in nums
            if n in {2, 3, 5, 7, 11, 13, 17, 19, 23}
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
        14: 10,
        15: 15
    }

    return pesos.get(acertos, 0)


def parse_numeros(valor):
    try:

        if isinstance(valor, list):
            return [int(x) for x in valor]

        if isinstance(valor, str):
            return [int(x) for x in json.loads(valor)]

    except:
        return None

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

    concurso_atual = concursos[0]["concurso"]

    dezenas_raw = concursos[0]["dezenas"]

    if isinstance(dezenas_raw, str):
        dezenas_oficiais = set(json.loads(dezenas_raw))
    else:
        dezenas_oficiais = set(dezenas_raw)

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

    if not palpites:
        print("⚠️ Nada para conferir")
        return

    print(f"📌 {len(palpites)} palpites")

    processados = 0

    for p in palpites:

        numeros = parse_numeros(
            p["numeros"]
        )

        if not numeros:
            continue

        acertos = len(
            set(numeros) & dezenas_oficiais
        )

        estrutura = extrair_estrutura(
            numeros
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

        memoria_payload = {
            **estrutura,
            "vezes_gerado": 1,
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        (
            supabase
            .table("memoria_cenarios")
            .upsert(
                memoria_payload,
                on_conflict="soma_faixa,pares,primos,linhas"
            )
            .execute()
        )

        resultado_payload = {
            "data_referencia": p["data_referencia"],
            "versao_gerador": p["versao_gerador"],
            "qtd_palpites": 1,
            "acertos_11": 1 if acertos == 11 else 0,
            "acertos_12": 1 if acertos == 12 else 0,
            "acertos_13": 1 if acertos == 13 else 0,
            "acertos_14": 1 if acertos == 14 else 0,
            "acertos_15": 1 if acertos == 15 else 0
        }

        (
            supabase
            .table("palpites_resultados_reais")
            .insert(resultado_payload)
            .execute()
        )

        processados += 1

    print(f"✅ {processados} palpites conferidos")


if __name__ == "__main__":
    main()
