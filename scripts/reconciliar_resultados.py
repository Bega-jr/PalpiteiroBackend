import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


def parse_numeros(valor):
    try:
        if isinstance(valor, list):
            return [int(x) for x in valor]

        if isinstance(valor, str):
            return [int(x) for x in json.loads(valor)]

    except Exception:
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


def obter_versao(p):
    metricas = p.get("metricas") or {}

    return (
        p.get("versao_gerador")
        or metricas.get("versao")
        or "legacy"
    )


def obter_resultado_oficial(supabase, concurso):

    result = (
        supabase
        .table("lotofacil_concursos")
        .select("dezenas")
        .eq("concurso", concurso)
        .limit(1)
        .execute()
        .data
    )

    if not result:
        return None

    dezenas_raw = result[0]["dezenas"]

    if isinstance(dezenas_raw, str):
        return set(json.loads(dezenas_raw))

    return set(dezenas_raw)


def main():

    supabase = get_supabase()

    print("🔄 Reconciliando resultados históricos...")

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nenhum palpite encontrado")
        return

    processados = 0

    for p in palpites:

        try:

            concurso = p["concurso_referencia"]

            dezenas_oficiais = obter_resultado_oficial(
                supabase,
                concurso
            )

            if not dezenas_oficiais:
                continue

            numeros = parse_numeros(
                p["numeros"]
            )

            if not numeros:
                continue

            acertos = len(
                set(numeros) & dezenas_oficiais
            )

            versao = obter_versao(
                p
            )

            # Atualiza acertos se estiver null
            if p.get("acertos") is None:

                (
                    supabase
                    .table("palpites_validos")
                    .update({
                        "acertos": acertos
                    })
                    .eq("id", p["id"])
                    .execute()
                )

            # Verifica se já existe em resultados
            existente = (
                supabase
                .table("palpites_resultados_reais")
                .select("id")
                .eq("data_referencia", p["data_referencia"])
                .eq("versao_gerador", versao)
                .eq("concurso_inicio", concurso)
                .limit(1)
                .execute()
                .data
            )

            if existente:
                continue

            peso = peso_acerto(
                acertos
            )

            payload = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": concurso,
                "concurso_fim": concurso,
                "versao_gerador": versao,

                "qtd_palpites": 1,

                "acertos_11": 1 if acertos == 11 else 0,
                "acertos_12": 1 if acertos == 12 else 0,
                "acertos_13": 1 if acertos == 13 else 0,
                "acertos_14": 1 if acertos == 14 else 0,
                "acertos_15": 1 if acertos == 15 else 0,

                "eficiencia": 1 if acertos >= 11 else 0,
                "score_ponderado": float(peso)
            }

            (
                supabase
                .table("palpites_resultados_reais")
                .insert(payload)
                .execute()
            )

            processados += 1

            print(
                f"✅ {concurso} | {versao} | {acertos} acertos"
            )

        except Exception as e:

            print(
                f"❌ Erro: {e}"
            )

    print(
        f"🏁 {processados} registros reconciliados"
    )


if __name__ == "__main__":
    main()
