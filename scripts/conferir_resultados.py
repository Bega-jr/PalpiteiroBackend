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
        "primos": sum(1 for n in nums if n in {2,3,5,7,11,13,17,19,23}),
        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }


def peso_acerto(acertos):
    return {
        11: 1,
        12: 2,
        13: 5,
        14: 20,
        15: 100
    }.get(acertos, 0)


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
    concurso_atual = concursos[0]["concurso"]

    # 🔥 CORREÇÃO AQUI
    concurso_referencia = concurso_atual - 1

    print(f"📊 Conferindo palpites do concurso {concurso_referencia}")

    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .eq("concurso_referencia", concurso_referencia) \
        .execute().data

    if not palpites:
        print("⚠️ Sem palpites para conferir")
        return

    for p in palpites:
        nums = set(json.loads(p["numeros"]))
        acertos = len(nums & dezenas)

        estrutura = extrair_estrutura(list(nums))
        peso = peso_acerto(acertos)

        supabase.table("memoria_cenarios").upsert({
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }, on_conflict="soma_faixa,pares,primos,linhas").execute()

        print(f"✔ Atualizado cenário | acertos={acertos} | peso={peso}")

    print("✅ Memória atualizada com sucesso")


if __name__ == "__main__":
    main()
