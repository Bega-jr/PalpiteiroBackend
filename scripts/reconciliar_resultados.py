import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


def parse_numeros(valor):

    if isinstance(valor, list):
        return [int(x) for x in valor]

    if isinstance(valor, str):
        try:
            return [int(x) for x in json.loads(valor)]
        except:
            return None

    return None


def parse_metricas(metricas):

    if not metricas:
        return {}

    if isinstance(metricas, dict):
        return metricas

    if isinstance(metricas, str):
        try:
            return json.loads(metricas)
        except:
            return {}

    return {}


def peso_acerto(acertos):

    pesos = {
        11: 1,
        12: 2,
        13: 5,
        14: 10,
        15: 15
    }

    return pesos.get(acertos, 0)


def main():

    supabase = get_supabase()

    print("🔄 Reconciliando resultados históricos...")

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
        .data
    )

    concurso_atual = concursos[0]["concurso"]

    dezenas_raw = concursos[0]["dezenas"]

    dezenas_oficiais = (
        set(json.loads(dezenas_raw))
        if isinstance(dezenas_raw, str)
        else set(dezenas_raw)
    )

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

            numeros = parse_numeros(
                p["numeros"]
            )

            if not numeros:
                continue

            acertos = len(
                set(numeros) & dezenas_oficiais
            )

            metricas = parse_metricas(
                p.get("metricas")
            )

            versao = (
                p.get("versao_gerador")
                or metricas.get("versao")
                or "legacy"
            )

            tipo_palpite = (
                p.get("tipo_palpite")
                or "estatistico"
            )

            peso = peso_acerto(
                acertos
            )

            # atualiza palpites_validos
            (
                supabase
                .table("palpites_validos")
                .update({
                    "acertos": acertos
                })
                .eq("id", p["id"])
                .execute()
            )

            payload = {

                "data_referencia": p["data_referencia"],

                "concurso_inicio":
                    p["concurso_referencia"],

                "concurso_fim":
                    p["concurso_referencia"],

                "tipo_palpite":
                    tipo_palpite,

                "versao_gerador":
                    versao,

                "qtd_palpites": 1,

                "acertos_11":
                    1 if acertos == 11 else 0,

                "acertos_12":
                    1 if acertos == 12 else 0,

                "acertos_13":
                    1 if acertos == 13 else 0,

                "acertos_14":
                    1 if acertos == 14 else 0,

                "acertos_15":
                    1 if acertos == 15 else 0,

                "score_ponderado":
                    float(peso),

                "eficiencia":
                    1 if acertos >= 11 else 0,

                "taxa_15":
                    1 if acertos == 15 else 0,

                "taxa_14":
                    1 if acertos == 14 else 0,

                "taxa_13":
                    1 if acertos == 13 else 0,

                "taxa_12":
                    1 if acertos == 12 else 0
            }

            (
                supabase
                .table("palpites_resultados_reais")
                .insert(payload)
                .execute()
            )

            reconciliados += 1

        except Exception as e:

            print(
                f"❌ Erro: {e}"
            )

    print(
        f"🏁 {reconciliados} registros reconciliados"
    )


if __name__ == "__main__":
    main()
