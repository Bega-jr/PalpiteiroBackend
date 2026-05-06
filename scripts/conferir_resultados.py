import sys
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


def parse_numeros(valor):

    if not valor:
        return None

    if isinstance(valor, list):
        try:
            return [int(x) for x in valor]
        except:
            return None

    if isinstance(valor, str):

        try:
            parsed = json.loads(valor)

            if isinstance(parsed, list):
                return [int(x) for x in parsed]

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


def buscar_resultados_oficiais(supabase):

    rows = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .execute()
        .data
    )

    resultados = {}

    for row in rows:

        try:

            concurso = int(
                row["concurso"]
            )

            dezenas = row.get(
                "dezenas"
            )

            if not dezenas:
                continue

            if isinstance(
                dezenas,
                str
            ):
                dezenas = json.loads(
                    dezenas
                )

            if not dezenas:
                continue

            if len(dezenas) != 15:
                continue

            resultados[concurso] = set(
                int(x) for x in dezenas
            )

        except:

            continue

    return resultados


def registro_ja_existe(
    supabase,
    data_referencia,
    concurso,
    tipo_palpite,
    versao
):

    row = (
        supabase
        .table("palpites_resultados_reais")
        .select("id")
        .eq(
            "data_referencia",
            data_referencia
        )
        .eq(
            "concurso_inicio",
            concurso
        )
        .eq(
            "tipo_palpite",
            tipo_palpite
        )
        .eq(
            "versao_gerador",
            versao
        )
        .limit(1)
        .execute()
        .data
    )

    return len(row) > 0


def main():

    supabase = get_supabase()

    print(
        "🏁 Conferindo resultados..."
    )

    resultados_oficiais = (
        buscar_resultados_oficiais(
            supabase
        )
    )

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .execute()
        .data
    )

    if not palpites:

        print(
            "⚠️ Nada para conferir"
        )

        return

    print(
        f"📌 {len(palpites)} palpites pendentes"
    )

    processados = 0

    for p in palpites:

        try:

            try:

                concurso = int(
                    p["concurso_referencia"]
                )

            except:

                print(
                    f"⚠️ Concurso inválido no palpite {p['id']}"
                )

                continue

            if concurso not in resultados_oficiais:

                print(
                    f"⚠️ Concurso {concurso} ainda sem resultado oficial"
                )

                continue

            numeros = parse_numeros(
                p["numeros"]
            )

            if not numeros:

                print(
                    f"⚠️ Números inválidos no palpite {p['id']}"
                )

                continue

            dezenas_oficiais = (
                resultados_oficiais[
                    concurso
                ]
            )

            metricas = parse_metricas(
                p.get("metricas")
            )

            versao = (
                p.get(
                    "versao_gerador"
                )
                or metricas.get(
                    "versao"
                )
                or "legacy"
            )

            tipo_palpite = (
                p.get(
                    "tipo_palpite"
                )
                or "estatistico"
            )

            acertos = len(
                set(numeros)
                &
                dezenas_oficiais
            )

            if registro_ja_existe(
                supabase,
                p["data_referencia"],
                concurso,
                tipo_palpite,
                versao
            ):

                print(
                    f"♻️ Já registrado: {concurso}"
                )

                (
                    supabase
                    .table(
                        "palpites_validos"
                    )
                    .update({
                        "acertos":
                            acertos
                    })
                    .eq(
                        "id",
                        p["id"]
                    )
                    .execute()
                )

                continue

            peso = peso_acerto(
                acertos
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

                "total_concursos":
                    1,

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
                .table(
                    "palpites_resultados_reais"
                )
                .insert(
                    payload
                )
                .execute()
            )

            (
                supabase
                .table(
                    "palpites_validos"
                )
                .update({
                    "acertos":
                        acertos
                })
                .eq(
                    "id",
                    p["id"]
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
