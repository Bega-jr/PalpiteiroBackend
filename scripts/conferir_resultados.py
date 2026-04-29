import sys
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# ======================================================
# EXTRAI ESTRUTURA
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

# ======================================================
# PESO REAL
# ======================================================
def peso_acerto(acertos):
    return {
        11: 1,
        12: 2,
        13: 5,
        14: 20,
        15: 100
    }.get(acertos, 0)

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print("🏁 Conferindo resultados e atualizando memória...")

    concursos = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    if not concursos:
        print("❌ Sem concurso")
        return

    dezenas = set(map(int, concursos[0]["dezenas"]))
    concurso_ref = concursos[0]["concurso"]

    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .eq("concurso_referencia", concurso_ref) \
        .execute().data

    if not palpites:
        print("⚠️ Sem palpites para conferir")
        return

    for p in palpites:
        nums = set(eval(p["numeros"]))
        acertos = len(nums & dezenas)

        estrutura = extrair_estrutura(list(nums))

        peso = peso_acerto(acertos)

        supabase.table("memoria_cenarios").update({
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }).match({
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"]
        }).execute()

    print("✅ Memória atualizada com desempenho real")


if __name__ == "__main__":
    main()
