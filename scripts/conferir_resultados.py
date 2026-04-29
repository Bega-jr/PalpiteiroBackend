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
# PESO DO ACERTO
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
# LEITURA SEGURA DOS NÚMEROS
# ======================================================
def parse_numeros(n):
    try:
        if isinstance(n, list):
            return n
        if isinstance(n, str):
            return json.loads(n)
    except:
        return None
    return None

# ======================================================
# MAIN
# ======================================================
def main():
    supabase = get_supabase()

    print("🏁 Conferindo resultados (modo robusto)...")

    # 🔹 Último concurso oficial
    concursos = supabase.table("lotofacil_concursos") \
        .select("concurso, dezenas") \
        .order("concurso", desc=True) \
        .limit(1) \
        .execute().data

    if not concursos:
        print("❌ Nenhum concurso encontrado")
        return

    concurso_atual = concursos[0]["concurso"]
    dezenas = set(map(int, concursos[0]["dezenas"]))

    print(f"📊 Concurso atual: {concurso_atual}")

    # 🔹 Buscar palpites NÃO conferidos
    palpites = supabase.table("palpites_validos") \
        .select("*") \
        .is_("acertos", None) \
        .order("concurso_referencia", desc=True) \
        .limit(200) \
        .execute().data

    if not palpites:
        print("⚠️ Nenhum palpite pendente para conferência")
        return

    # 🔹 Evita conferir concurso atual
    palpites = [
        p for p in palpites
        if p["concurso_referencia"] < concurso_atual
    ]

    if not palpites:
        print("⚠️ Nenhum palpite válido para conferência (todos são do concurso atual)")
        return

    print(f"📌 {len(palpites)} palpites pendentes encontrados")

    sucesso = 0

    for p in palpites:
        numeros = parse_numeros(p["numeros"])

        if not numeros:
            print(f"⚠️ Erro ao ler numeros ID={p['id']}")
            continue

        nums = set(map(int, numeros))
        acertos = len(nums & dezenas)

        estrutura = extrair_estrutura(list(nums))
        peso = peso_acerto(acertos)

        # ==================================================
        # ATUALIZA PALPITE (marca como conferido)
        # ==================================================
        supabase.table("palpites_validos").update({
            "acertos": acertos
        }).eq("id", p["id"]).execute()

        # ==================================================
        # ATUALIZA MEMÓRIA (UPSERT + ACUMULADO)
        # ==================================================
        supabase.table("memoria_cenarios").upsert({
            "soma_faixa": estrutura["soma_faixa"],
            "pares": estrutura["pares"],
            "primos": estrutura["primos"],
            "linhas": estrutura["linhas"],
            "vezes_gerado": 1,
            f"acertos_{acertos}": 1,
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }, on_conflict="soma_faixa,pares,primos,linhas").execute()

        sucesso += 1

    print(f"✅ {sucesso} palpites conferidos com sucesso")


if __name__ == "__main__":
    main()
