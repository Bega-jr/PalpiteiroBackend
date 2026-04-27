import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# ======================================================
# AUX
# ======================================================
def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }


def calcular_acertos(palpite, resultado):
    return len(set(palpite) & set(resultado))


def peso_acerto(acertos):
    if acertos == 11: return 0.05
    if acertos == 12: return 0.15
    if acertos == 13: return 0.40
    if acertos == 14: return 0.80
    if acertos == 15: return 1.00
    return 0


# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print("🧠 Atualizando memória com resultado real...")

    # último concurso
    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True).limit(1).execute().data[0]

    concurso_ref = concurso["concurso"]
    resultado = list(map(int, concurso["dezenas"]))

    print(f"📌 Concurso {concurso_ref}")

    # palpites gerados
    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .eq("concurso_referencia", concurso_ref) \
        .execute().data

    if not palpites:
        print("❌ Nenhum palpite encontrado")
        return

    for p in palpites:
        numeros = eval(p["numeros"]) if isinstance(p["numeros"], str) else p["numeros"]

        acertos = calcular_acertos(numeros, resultado)
        peso = peso_acerto(acertos)

        estrutura = extrair_estrutura(numeros)

        # busca cenário
        res = supabase.table("memoria_cenarios") \
            .select("*") \
            .eq("soma_faixa", estrutura["soma_faixa"]) \
            .eq("pares", estrutura["pares"]) \
            .eq("primos", estrutura["primos"]) \
            .execute()

        if not res.data:
            continue

        row = res.data[0]

        vezes = row.get("vezes_gerado", 0) + 1
        score_antigo = float(row.get("score_medio_real", 0))

        novo_score = ((score_antigo * (vezes - 1)) + peso) / vezes

        update = {
            "vezes_gerado": vezes,
            "score_medio_real": round(novo_score, 4),
            "ultima_aparicao": datetime.now().date().isoformat(),
            f"acertos_{acertos}": row.get(f"acertos_{acertos}", 0) + 1
        }

        supabase.table("memoria_cenarios") \
            .update(update) \
            .eq("id", row["id"]) \
            .execute()

    print("✅ Memória atualizada com aprendizado real")


if __name__ == "__main__":
    main()
