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


def dezenas_validas(valor):

    dezenas = parse_numeros(valor)

    if not dezenas:
        return None

    if len(dezenas) != 15:
        return None

    return set(dezenas)


def resultado_ja_existe(
    supabase,
    data_referencia,
    concurso,
    tipo_palpite
):

    resultado = (
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
        .limit(1)
        .execute()
        .data
    )

    return len(resultado) > 0


def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("conferido", False)
        .execute()
        .data
    )

    if not palpites:

        print("⚠️ Nada para conferir")
        return

    print(
        f"📌 {len(palpites)} palpites pendentes"
    )

    concursos_ids = list(
        set(
            p["concurso_referencia"]
            for p in palpites
        )
    )

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .in_("concurso", concursos_ids)
        .execute()
        .data
    )

    mapa_concursos = {}

    for c in concursos:

        dezenas = dezenas_validas(
            c.get("dezenas")
        )

        if dezenas:

            mapa_concursos[
                c["concurso"]
            ] = dezenas

    processados = 0
    ignorados = 0

    for p in palpites:

        try:

            concurso = p[
                "concurso_referencia"
            ]

            dezenas_oficiais = (
                mapa_concursos.get(
                    concurso
                )
            )

            if not dezenas_oficiais:

                print(
                    f"⚠️ Concurso {concurso} sem resultado válido"
                )

                ignorados += 1
                continue

            numeros = parse_numeros(
                p["numeros"]
            )

            if not numeros:

                continue

            metricas = parse_metricas(
                p.get("metricas")
            )

            versao = (
                p.get("versao_gerador")
                or metricas.get("v")
                or "legacy"
            )

            tipo_palpite = (
                p.get("tipo")
                or p.get("tipo_palpite")
                or "estatistico"
            )

            acertos = len(
                set(numeros)
                & dezenas_oficiais
            )

            peso = peso_acerto(
                acertos
            )

            if not resultado_ja_existe(
                supabase,
                p["data_referencia"],
                concurso,
                tipo_palpite
            ):

                payload = {

                    "data_referencia":
                        p["data_referencia"],

                    "concurso_inicio":
                        concurso,

                    "concurso_fim":
                        concurso,

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
                    .table(
                        "palpites_resultados_reais"
                    )
                    .insert(payload)
                    .execute()
                )

            (
                supabase
                .table("palpites_validos")
                .update({
                    "acertos": acertos,
                    "conferido": True,
                    "processado": True
                })
                .eq("id", p["id"])
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

    if ignorados:

        print(
            f"⚠️ {ignorados} ignorados"
        )


if __name__ == "__main__":
    main()
