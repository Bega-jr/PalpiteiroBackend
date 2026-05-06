import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


# =========================
# PARSER ROBUSTO
# =========================
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
# MAIN
# =========================
def main():

    supabase = get_supabase()

    print("🔄 Reconciliando resultados históricos...")

    # pega último concurso oficial
    concurso = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
        .data
    )[0]

    concurso_atual = int(concurso["concurso"])

    dezenas_raw = concurso["dezenas"]

    dezenas = parse_numeros(dezenas_raw)

    if not dezenas:
        print("❌ Concurso oficial inválido")
        return

    oficiais = set(dezenas)

    # pega apenas pendentes antigos
    pendentes = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .lt("concurso_referencia", concurso_atual)
        .execute()
        .data
    )

    if not pendentes:
        print("✅ Nada pendente")
        return

    reconciliados = 0

    for p in pendentes:

        try:

            numeros = parse_numeros(p["numeros"])

            if not numeros:
                continue

            acertos = len(set(numeros) & oficiais)

            peso = peso_acerto(acertos)

            # 🔥 FIX CRÍTICO: evitar null constraint
            payload = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": p["concurso_referencia"],
                "concurso_fim": p["concurso_referencia"],
                "total_concursos": 1,  # <<< FIX AQUI
                "tipo_palpite": p.get("tipo_palpite") or "estatistico",
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

            # evita duplicação silenciosa
            exists = (
                supabase
                .table("palpites_resultados_reais")
                .select("id")
                .eq("concurso_inicio", p["concurso_referencia"])
                .eq("versao_gerador", payload["versao_gerador"])
                .limit(1)
                .execute()
                .data
            )

            if not exists:

                supabase.table("palpites_resultados_reais") \
                    .insert(payload) \
                    .execute()

            # atualiza base principal
            supabase.table("palpites_validos") \
                .update({"acertos": acertos}) \
                .eq("id", p["id"]) \
                .execute()

            reconciliados += 1

        except Exception as e:
            print(f"❌ Erro: {e}")

    print(f"🏁 {reconciliados} registros reconciliados")


if __name__ == "__main__":
    main()
