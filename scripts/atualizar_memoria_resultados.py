import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

PRIMOS = {2, 3, 5, 7, 11, 13, 17, 19, 23}


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
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in PRIMOS),
        "hash_estrutura": "-".join(map(str, linhas))
    }


def calcular_acertos(palpite, resultado):
    return len(set(palpite) & set(resultado))


def peso_acerto(acertos):
    pesos = {
        11: 0.10,
        12: 0.25,
        13: 0.50,
        14: 0.80,
        15: 1.00
    }
    return pesos.get(acertos, 0.02)


def score_v15(row):
    """
    🧠 SCORE INTELIGENTE
    """
    return (
        row.get("score_medio_real", 0) * 0.5 +
        row.get("taxa_7d", 0) * 0.3 +
        row.get("taxa_30d", 0) * 0.2
    )


def main():
    supabase = get_supabase()

    print("🧠 Atualizando memória v15")

    concurso = supabase.table(
        "lotofacil_concursos"
    ).select(
        "concurso,dezenas"
    ).order(
        "concurso",
        desc=True
    ).limit(1).execute().data[0]

    concurso_ref = int(concurso["concurso"])
    resultado = parse_numeros(concurso["dezenas"])

    palpites = supabase.table(
        "palpites_validos"
    ).select("*").eq(
        "concurso_referencia",
        concurso_ref
    ).execute().data

    if not palpites:
        print("⚠️ Nenhum palpite encontrado")
        return

    for p in palpites:

        numeros = parse_numeros(p["numeros"])
        if not numeros:
            continue

        estrutura = extrair_estrutura(numeros)
        acertos = calcular_acertos(numeros, resultado)
        peso = peso_acerto(acertos)

        busca = supabase.table(
            "memoria_cenarios"
        ).select("*").eq(
            "hash_estrutura",
            estrutura["hash_estrutura"]
        ).execute()

        if not busca.data:
            continue

        row = busca.data[0]

        vezes = row.get("vezes_gerado", 0)
        score_antigo = row.get("score_medio_real", 0)

        novo_vezes = vezes + 1

        # 🧠 atualização base
        score_novo = (
            (score_antigo * vezes) + peso
        ) / novo_vezes

        # 🔥 boost por performance recente
        taxa_7d = row.get("taxa_7d", 0)
        taxa_30d = row.get("taxa_30d", 0)

        score_final = (
            score_novo * 0.7 +
            taxa_7d * 0.2 +
            taxa_30d * 0.1
        )

        update = {
            "vezes_gerado": novo_vezes,
            "score_medio_real": round(score_novo, 4),
            "score_v15": round(score_final, 4),
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        # 📈 distribuição de acertos
        if acertos >= 11:
            col = f"acertos_{acertos}"
            update[col] = row.get(col, 0) + 1

        supabase.table(
            "memoria_cenarios"
        ).update(update).eq(
            "id",
            row["id"]
        ).execute()

    print("✅ Memória v15 atualizada")


if __name__ == "__main__":
    main()
