import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


def parse_numeros(valor):

    if not valor:
        return None

    try:

        if isinstance(valor, list):
            return [int(x) for x in valor]

        if isinstance(valor, str):

            parsed = json.loads(valor)

            if isinstance(parsed, str):
                parsed = json.loads(parsed)

            if isinstance(parsed, list):
                return [int(x) for x in parsed]

    except:
        return None

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


def carregar_concursos(supabase):

    rows = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .execute()
        .data
    )

    mapa = {}

    for r in rows:

        concurso = int(r["concurso"])
        dezenas = parse_numeros(r["dezenas"])

        if not dezenas or len(dezenas) != 15:
            continue

        mapa[concurso] = set(dezenas)

    print(f"📊 Concursos carregados: {len(mapa)}")

    return mapa


def ja_existe(supabase, palpite_id):

    row = (
        supabase
        .table("palpites_resultados_reais")
        .select("id")
        .eq("palpite_id", palpite_id)
        .limit(1)
        .execute()
        .data
    )

    return len(row) > 0


def main():

    supabase = get_supabase()

    print("🔄 Reconciliando resultados históricos...")

    concursos = carregar_concursos(supabase)

    if not concursos:
        print("❌ Nenhum concurso carregado")
        return

    pendentes = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .execute()
        .data
    )

    if not pendentes:
        print("✅ Nada pendente")
        return

    print(f"📌 {len(pendentes)} palpites pendentes")

    total = 0

    for p in pendentes:

        try:

            concurso = int(p["concurso_referencia"])

            if concurso not in concursos:
                print(f"⏳ Concurso {concurso} ainda sem resultado oficial")
                continue

            numeros = parse_numeros(p["numeros"])

            if not numeros:
                continue

            oficiais = concursos[concurso]

            acertos = len(set(numeros) & oficiais)

            # evita duplicar resultado
            if ja_existe(supabase, p["id"]):
                continue

            peso = peso_acerto(acertos)

            # atualiza palpite
            supabase.table("palpites_validos").update({
                "acertos": acertos
            }).eq("id", p["id"]).execute()

            payload = {
                "palpite_id": p["id"],
                "data_referencia": p["data_referencia"],
                "concurso_inicio": concurso,
                "concurso_fim": concurso,
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

            supabase.table("palpites_resultados_reais").insert(payload).execute()

            total += 1

            print(f"✅ Concurso {concurso} | {acertos} acertos")

        except Exception as e:
            print(f"❌ Erro: {e}")

    print(f"🏁 {total} registros reconciliados")


if __name__ == "__main__":
    main()
