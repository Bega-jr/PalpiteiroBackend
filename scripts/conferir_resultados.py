import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


# ======================================================
# ESTRUTURA
# ======================================================
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


# ======================================================
# PESO REAL
# ======================================================
def peso_acerto(acertos):
    pesos = {
        11: 1,
        12: 2,
        13: 5,
        14: 20,
        15: 100
    }

    return pesos.get(acertos, 0)


# ======================================================
# LEITURA SEGURA
# ======================================================
def parse_numeros(valor):
    try:
        if isinstance(valor, list):
            return [int(x) for x in valor]

        if isinstance(valor, str):
            return [int(x) for x in json.loads(valor)]

    except Exception:
        return None

    return None


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    # Último concurso oficial
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
        print("❌ Nenhum concurso encontrado")
        return

    concurso_atual = concursos[0]["concurso"]

    dezenas_raw = concursos[0]["dezenas"]

    if isinstance(dezenas_raw, str):
        dezenas_oficiais = set(json.loads(dezenas_raw))
    else:
        dezenas_oficiais = set(dezenas_raw)

    print(f"📌 {concurso_atual}")

    # Busca palpites pendentes
    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .order("concurso_referencia", desc=True)
        .limit(200)
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nenhum palpite pendente")
        return

    # Não conferir concurso atual
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

        numeros = parse_numeros(p["numeros"])

        if not numeros:
            continue

        nums_set = set(numeros)

        acertos = len(nums_set & dezenas_oficiais)

        estrutura = extrair_estrutura(numeros)

        peso = peso_acerto(acertos)

        # Marca palpite conferido
        (
            supabase
            .table("palpites_validos")
            .update({
                "acertos": acertos
            })
            .eq("id", p["id"])
            .execute()
        )

        # Payload seguro
               payload_memoria = {
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "vezes_gerado": 1,
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        if acertos >= 11:
            payload_memoria[f"acertos_{acertos}"] = 1
        (
            supabase
            .table("memoria_cenarios")
            .upsert(
                payload,
                on_conflict="soma_faixa,pares,primos,linhas"
            )
            .execute()
        )

        processados += 1

    print(f"✅ {processados} palpites conferidos")


if __name__ == "__main__":
    main()
