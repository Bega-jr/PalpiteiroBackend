import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


# =========================
# PARSER ROBUSTO (FIX BUG)
# =========================
def parse_numeros(valor):

    if not valor:
        return None

    try:

        # já lista
        if isinstance(valor, list):
            return [int(x) for x in valor]

        if isinstance(valor, str):

            parsed = json.loads(valor)

            # caso venha dupla string "\"[1,2,3]\""
            if isinstance(parsed, str):
                parsed = json.loads(parsed)

            if isinstance(parsed, list):
                return [int(x) for x in parsed]

    except Exception as e:
        print(f"⚠️ Parse erro: {e}")

    return None


def peso_acerto(acertos):

    pesos = {
        11: 1,
        12: 2,
        13: 5,
        14: 10,
        15: 15
    }

    return pesos.get(acertos, 0)


# =========================
# RESULTADOS OFICIAIS
# =========================
def buscar_resultados_oficiais(supabase):

    rows = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .execute()
        .data
    )

    resultados = {}

    print(f"📊 Concursos oficiais encontrados: {len(rows)}")

    for row in rows:

        try:
            concurso = int(row["concurso"])
            dezenas = parse_numeros(row.get("dezenas"))

            if not dezenas or len(dezenas) != 15:
                continue

            resultados[concurso] = set(dezenas)

        except Exception as e:
            print(f"⚠️ Erro concurso: {e}")

    print(f"✅ Concursos válidos carregados: {len(resultados)}")

    return resultados


# =========================
# MAIN
# =========================
def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    resultados = buscar_resultados_oficiais(supabase)

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nada para conferir")
        return

    print(f"📌 {len(palpites)} palpites pendentes")

    processados = 0
    ignorados = {}

    for p in palpites:

        try:

            concurso = int(p["concurso_referencia"])

            # ainda não saiu resultado
            if concurso not in resultados:
                ignorados[concurso] = ignorados.get(concurso, 0) + 1
                continue

            numeros = parse_numeros(p["numeros"])

            if not numeros:
                print(f"⚠️ Palpite inválido {p['id']}")
                continue

            oficiais = resultados[concurso]

            acertos = len(set(numeros) & oficiais)

            peso = peso_acerto(acertos)

            payload = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": concurso,
                "concurso_fim": concurso,
                "total_concursos": 1,
                "tipo_palpite": p.get("tipo") or "estatistico",
                "versao_gerador": p.get("versao_gerador") or "legacy",
                "qtd_palpites": 1,

                "acertos_11": 1 if acertos == 11 else 0,
                "acertos_12": 1 if acertos == 12 else 0,
                "acertos_13": 1 if acertos == 13 else 0,
                "acertos_14": 1 if acertos == 14 else 0,
                "acertos_15": 1 if acertos == 15 else 0,

                "score_ponderado": float(peso),
                "eficiencia": 1 if acertos >= 11 else 0,

                "taxa_15": 1 if acertos == 15 else 0,
                "taxa_14": 1 if acertos == 14 else 0,
                "taxa_13": 1 if acertos == 13 else 0,
                "taxa_12": 1 if acertos == 12 else 0
            }

            # salva histórico real
            supabase.table("palpites_resultados_reais").insert(payload).execute()

            # atualiza base principal
            supabase.table("palpites_validos") \
                .update({"acertos": acertos}) \
                .eq("id", p["id"]) \
                .execute()

            print(f"✅ Concurso {concurso}: {acertos} acertos")

            processados += 1

        except Exception as e:
            print(f"❌ Erro {p['id']}: {e}")

    # resumo inteligente
    if ignorados:
        print("\n⏳ Aguardando resultados oficiais:")
        for k, v in sorted(ignorados.items()):
            print(f"   - Concurso {k}: {v} palpites")

    print(f"\n✅ {processados} palpites conferidos")


if __name__ == "__main__":
    main()
