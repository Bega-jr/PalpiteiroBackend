import sys
import json
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

    print("🏁 Conferindo resultados (modo robusto)...")

    # 🔥 último resultado oficial
    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1).execute().data

    if not concurso:
        print("❌ Sem concurso disponível")
        return

    dezenas = set(map(int, concurso[0]["dezenas"]))
    concurso_atual = concurso[0]["concurso"]

    print(f"📊 Concurso atual: {concurso_atual}")

    # ==================================================
    # 🔥 BUSCAR TODOS NÃO CONFERIDOS
    # ==================================================
    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .eq("conferido", False) \
        .execute().data

    if not palpites:
        print("✅ Nenhum palpite pendente")
        return

    print(f"📌 {len(palpites)} palpites pendentes encontrados")

    atualizados = 0

    for p in palpites:
        try:
            nums = set(json.loads(p["numeros"]))
        except:
            print(f"⚠️ Erro ao ler numeros ID={p.get('id')}")
            continue

        acertos = len(nums & dezenas)

        estrutura = extrair_estrutura(list(nums))
        peso = peso_acerto(acertos)

        # ==================================================
        # UPSERT NA MEMÓRIA
        # ==================================================
        supabase.table("memoria_cenarios").upsert({
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }, on_conflict="soma_faixa,pares,primos,linhas").execute()

        # ==================================================
        # MARCAR COMO CONFERIDO
        # ==================================================
        supabase.table("palpites_validos") \
            .update({"conferido": True}) \
            .eq("id", p["id"]) \
            .execute()

        print(f"✔ ID={p['id']} | acertos={acertos} | peso={peso}")

        atualizados += 1

    print(f"\n✅ {atualizados} palpites conferidos com sucesso")


if __name__ == "__main__":
    main()
