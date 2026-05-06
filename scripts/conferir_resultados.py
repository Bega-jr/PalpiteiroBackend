import sys
import json
from pathlib import Path
from collections import defaultdict

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


def obter_resultados_oficiais(supabase):

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .execute()
        .data
    )

    mapa = {}

    for c in concursos:

        dezenas = c["dezenas"]

        if isinstance(dezenas, str):
            dezenas = json.loads(dezenas)

        mapa[c["concurso"]] = set(dezenas)

    return mapa


def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    resultados_oficiais = obter_resultados_oficiais(
        supabase
    )

    if not resultados_oficiais:
        print("❌ Sem concursos oficiais")
        return

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("conferido", False)
        .eq("processado", False)
        .order("concurso_referencia")
        .order("indice_palpite")
        .limit(500)
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nada para conferir")
        return

    print(
        f"📌 {len(palpites)} palpites pendentes"
    )

    grupos = defaultdict(list)

    for p in palpites:

        concurso = p.get(
            "concurso_referencia"
        )

        grupos[concurso].append(
            p
        )

    processados = 0

    for concurso, apostas in grupos.items():

        dezenas_oficiais = (
            resultados_oficiais.get(
                concurso
            )
        )

        if not dezenas_oficiais:

            print(
                f"⚠️ Concurso {concurso} ainda sem resultado oficial"
            )

            continue

        print(
            f"📌 Concurso {concurso}: {len(apostas)} palpites"
        )

        for p in apostas:

            try:

                numeros = parse_numeros(
                    p["numeros"]
                )

                if not numeros:
                    continue

                metricas = parse_metricas(
                    p.get(
                        "metricas"
                    )
                )

                versao = (
                    p.get(
                        "versao_gerador"
                    )
                    or metricas.get(
                        "versao"
                    )
                    or metricas.get(
                        "v"
                    )
                    or "legacy"
                )

                tipo_palpite = (
                    p.get(
                        "tipo"
                    )
                    or p.get(
                        "tipo_palpite"
                    )
                    or "estatistico"
                )

                acertos = len(
                    set(numeros)
                    & dezenas_oficiais
                )

                peso = peso_acerto(
                    acertos
                )

                # atualiza origem
                (
                    supabase
                    .table(
                        "palpites_validos"
                    )
                    .update({
                        "acertos":
                            acertos,
                        "conferido":
                            True,
                        "processado":
                            True
                    })
                    .eq(
                        "id",
                        p["id"]
                    )
                    .execute()
                )

                payload = {

                    "data_referencia":
                        p[
                            "data_referencia"
                        ],

                    "concurso_inicio":
                        concurso,

                    "concurso_fim":
                        concurso,

                    "tipo_palpite":
                        tipo_palpite,

                    "versao_gerador":
                        versao,

                    "qtd_palpites":
                        1,

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
                        float(
                            peso
                        ),

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
                    .table(
                        "palpites_resultados_reais"
                    )
                    .insert(
                        payload
                    )
                    .execute()
                )

                processados += 1

            except Exception as e:

                print(
                    f"❌ Erro no palpite {p['id']}: {e}"
                )

    print(
        f"✅ {processados} palpites conferidos"
    )


if __name__ == "__main__":
    main()
