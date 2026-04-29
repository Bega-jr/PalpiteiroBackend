import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase

# ======================================================
# PARSER ROBUSTO (resolve seu problema)
# ======================================================
def parse_numeros(raw):
    try:
        # já é lista
        if isinstance(raw, list):
            return list(map(int, raw))

        # tenta json normal
        try:
            return list(map(int, json.loads(raw)))
        except:
            pass

        # remove aspas duplicadas "\"[...]\""
        cleaned = raw.strip().replace('\\"', '"').strip('"')

        return list(map(int, json.loads(cleaned)))

    except Exception:
        return None


# ======================================================
# ESTRUTURA
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

    concurso = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1).execute().data[0]

    concurso_ref = concurso["concurso"]
    dezenas = set(map(int, concurso["dezenas"]))

    print(f"📊 Concurso atual: {concurso_ref}")

    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .eq("concurso_referencia", concurso_ref) \
        .execute().data

    if not palpites:
        print("⚠️ Nenhum palpite encontrado")
        return

    print(f"📌 {len(palpites)} palpites encontrados")

    ok = 0

    for p in palpites:
        nums = parse_numeros(p["numeros"])

        if not nums:
            print(f"⚠️ Erro ao ler numeros ID={p['id']}")
            continue

        acertos = len(set(nums) & dezenas)

        estrutura = extrair_estrutura(nums)
        peso = peso_acerto(acertos)

        # Atualiza memória (acumulando aprendizado)
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

        ok += 1

    print(f"✅ {ok} palpites conferidos com sucesso")


if __name__ == "__main__":
    main()
