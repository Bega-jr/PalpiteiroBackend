import sys
import json

from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


# ======================================================
# AUX
# ======================================================
PRIMOS = {2,3,5,7,11,13,17,19,23}


def parse_numeros(valor):
    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):
        return [int(x) for x in json.loads(valor)]

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
        "linhas": linhas,
        "hash_estrutura": "-".join(map(str, linhas))
    }


def calcular_acertos(palpite, resultado):
    return len(set(palpite) & set(resultado))


def peso_acerto(acertos):

    pesos = {
        11: 0.05,
        12: 0.15,
        13: 0.40,
        14: 0.80,
        15: 1.00
    }

    return pesos.get(acertos, 0)


# ======================================================
# MAIN
# ======================================================
def main():

    supabase = get_supabase()

    print("🧠 Atualizando memória com resultados reais")

    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso,dezenas") \
        .order("concurso", desc=True) \
        .limit(1) \
        .execute() \
        .data[0]

    concurso_ref = int(concurso["concurso"])

    resultado = parse_numeros(
        concurso["dezenas"]
    )

    print(f"📌 Concurso {concurso_ref}")

    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .eq("concurso_referencia", concurso_ref) \
        .execute() \
        .data

    if not palpites:
        print("⚠️ Nenhum palpite encontrado")
        return

    atualizados = 0

    for p in palpites:

        numeros = parse_numeros(
            p["numeros"]
        )

        if not numeros:
            continue

        acertos = calcular_acertos(
            numeros,
            resultado
        )

        estrutura = extrair_estrutura(
            numeros
        )

        peso = peso_acerto(
            acertos
        )

        busca = supabase.table("memoria_cenarios") \
            .select("*") \
            .eq("soma_faixa", estrutura["soma_faixa"]) \
            .eq("pares", estrutura["pares"]) \
            .eq("primos", estrutura["primos"]) \
            .eq("hash_estrutura", estrutura["hash_estrutura"]) \
            .execute()

        if not busca.data:
            continue

        row = busca.data[0]

        vezes_antes = int(
            row.get("vezes_gerado", 0)
        )

        score_antigo = float(
            row.get("score_medio_real", 0)
        )

        novo_total = vezes_antes + 1

        novo_score = (
            (score_antigo * vezes_antes) + peso
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
                row.get(coluna, 0)
            ) + 1

        supabase.table("memoria_cenarios") \
            .update(update) \
            .eq("id", row["id"]) \
            .execute()

        atualizados += 1

    print(
        f"✅ {atualizados} cenários atualizados"
    )


if __name__ == "__main__":
    main()
