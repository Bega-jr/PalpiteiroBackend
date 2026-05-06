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

        # lista python / jsonb
        if isinstance(valor, list):

            numeros = [
                int(x)
                for x in valor
            ]

        # string json
        elif isinstance(valor, str):

            numeros = json.loads(
                valor
            )

            numeros = [
                int(x)
                for x in numeros
            ]

        else:

            return None

        if len(numeros) != 15:
            return None

        return sorted(numeros)

    except:

        return None


def parse_metricas(metricas):

    if not metricas:
        return {}

    try:

        if isinstance(
            metricas,
            dict
        ):
            return metricas

        if isinstance(
            metricas,
            str
        ):
            return json.loads(
                metricas
            )

    except:

        pass

    return {}


def peso_acerto(acertos):

    pesos = {
        11: 1,
        12: 2,
        13: 5,
        14: 10,
        15: 15
    }

    return pesos.get(
        acertos,
        0
    )


def buscar_resultados_oficiais(
    supabase
):

    rows = (
        supabase
        .table(
            "lotofacil_concursos"
        )
        .select(
            "concurso,dezenas"
        )
        .execute()
        .data
    )

    resultados = {}

    for row in rows:

        try:

            concurso = int(
                row["concurso"]
            )

            dezenas = parse_numeros(
                row["dezenas"]
            )

            if not dezenas:
                continue

            resultados[
                concurso
            ] = set(
                dezenas
            )

        except:

            continue

    return resultados


def registro_ja_existe(
    supabase,
    data_referencia,
    concurso,
    tipo,
    versao
):

    rows = (
        supabase
        .table(
            "palpites_resultados_reais"
        )
        .select(
            "id"
        )
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
            tipo
        )
        .eq(
            "versao_gerador",
            versao
        )
        .limit(1)
        .execute()
        .data
    )

    return len(
        rows
    ) > 0


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
        .table(
            "palpites_validos"
        )
        .select("*")
        .is_(
            "acertos",
            None
        )
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

            concurso = int(
                p[
                    "concurso_referencia"
                ]
            )

            if concurso not in resultados_oficiais:

                print(
                    f"⚠️ Concurso {concurso} ainda sem resultado oficial"
                )

                continue

            numeros = parse_numeros(
                p[
                    "numeros"
                ]
            )

            if not numeros:

                print(
                    f"⚠️ Palpite inválido: {p['id']}"
                )

                continue

            dezenas_oficiais = (
                resultados_oficiais[
                    concurso
                ]
            )

            metricas = (
                parse_metricas(
                    p.get(
                        "metricas"
                    )
                )
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

            # compatível com versões antigas e novas
            tipo = (
                p.get(
                    "tipo"
                )
                or p.get(
                    "tipo_palpite"
                )
                or "estatistico"
            )

            acertos = len(
                set(
                    numeros
                )
                &
                dezenas_oficiais
            )

            if registro_ja_existe(
                supabase,
                p[
                    "data_referencia"
                ],
                concurso,
                tipo,
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
                    tipo,

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

            print(
                f"✅ Concurso {concurso} | {acertos} acertos"
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
