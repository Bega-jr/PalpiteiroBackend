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


def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    # Apenas palpites ainda não conferidos
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

    print(f"📌 {len(palpites)} palpites pendentes")

    concursos_necessarios = sorted(
        list(
            set(
                p["concurso_referencia"]
                for p in palpites
            )
        )
    )

    # Busca todos concursos de uma vez
    concursos_db = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .in_("concurso", concursos_necessarios)
        .execute()
        .data
    )

    mapa_resultados = {}

    for c in concursos_db:

        dezenas = dezenas_validas(
            c.get("dezenas")
        )

        if dezenas:
            mapa_resultados[
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
                mapa_resultados.get(
                    concurso
                )
            )

            if not dezenas_oficiais:

                print(
                    f"⚠️ Concurso {concurso} sem dezenas válidas"
                )

                ignorados += 1
                continue

            numeros = parse_numeros(
                p["numeros"]
            )

            if not numeros:

                print(
                    f"⚠️ Palpite {p['id']} inválido"
                )

                continue

            metricas = parse_metricas(
                p.get("metricas")
            )

            versao = (
                p.get("versao_gerador")
                or metricas.get("v")
                or metricas.get("versao")
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

            # Atualiza origem
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

            # evita duplicidade futura
            (
                supabase
                .table("palpites_resultados_reais")
                .upsert(
                    payload,
                    on_conflict="data_referencia,concurso_inicio,tipo_palpite"
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

    if ignorados > 0:

        print(
            f"⚠️ {ignorados} ignorados por dados inválidos"
        )


if __name__ == "__main__":
    main()
