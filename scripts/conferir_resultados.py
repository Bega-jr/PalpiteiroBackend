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


def extrair_estrutura(nums):

    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),

        "pares": sum(
            1 for n in nums if n % 2 == 0
        ),

        "primos": sum(
            1 for n in nums
            if n in {2,3,5,7,11,13,17,19,23}
        ),

        "linhas": [
            sum(1 for n in nums if 1 <= n <= 5),
            sum(1 for n in nums if 6 <= n <= 10),
            sum(1 for n in nums if 11 <= n <= 15),
            sum(1 for n in nums if 16 <= n <= 20),
            sum(1 for n in nums if 21 <= n <= 25),
        ]
    }


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


def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    concurso = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso,dezenas")
        .order("concurso", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not concurso:
        print("❌ Sem concursos")
        return

    concurso_atual = concurso[0]["concurso"]

    dezenas_raw = concurso[0]["dezenas"]

    if isinstance(dezenas_raw, str):
        dezenas_oficiais = set(json.loads(dezenas_raw))
    else:
        dezenas_oficiais = set(dezenas_raw)

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .execute()
        .data
    )

    palpites = [
        p for p in palpites
        if p["concurso_referencia"] < concurso_atual
    ]

    if not palpites:
        print("⚠️ Nada para conferir")
        return

    print(f"📌 {len(palpites)} palpites")

    agrupados = {}

    for p in palpites:

        numeros = parse_numeros(
            p["numeros"]
        )

        if not numeros:
            continue

        acertos = len(
            set(numeros) & dezenas_oficiais
        )

        versao = obter_versao(p)

        peso = peso_acerto(acertos)

        estrutura = extrair_estrutura(
            numeros
        )

        # atualiza palpite
        (
            supabase
            .table("palpites_validos")
            .update({
                "acertos": acertos
            })
            .eq("id", p["id"])
            .execute()
        )

        # memória
        memoria = {
            **estrutura,
            "vezes_gerado": 1,
            "score_medio_real": peso,
            "ultima_aparicao": datetime.now().date().isoformat(),
            "updated_at": datetime.now().isoformat()
        }

        (
            supabase
            .table("memoria_cenarios")
            .upsert(
                memoria,
                on_conflict="soma_faixa,pares,primos,linhas"
            )
            .execute()
        )

        chave = (
            str(p["data_referencia"]),
            versao,
            p["concurso_referencia"]
        )

        if chave not in agrupados:

            agrupados[chave] = {
                "data_referencia": p["data_referencia"],
                "concurso_inicio": p["concurso_referencia"],
                "concurso_fim": p["concurso_referencia"],
                "versao_gerador": versao,
                "qtd_palpites": 0,
                "acertos_11": 0,
                "acertos_12": 0,
                "acertos_13": 0,
                "acertos_14": 0,
                "acertos_15": 0,
                "score_ponderado": 0
            }

        item = agrupados[chave]

        item["qtd_palpites"] += 1
        item["score_ponderado"] += peso

        if acertos >= 11:
            item[f"acertos_{acertos}"] += 1

    # grava agregados
    for item in agrupados.values():

        qtd = item["qtd_palpites"]

        item["eficiencia"] = (
            (
                item["acertos_11"]
                + item["acertos_12"]
                + item["acertos_13"]
                + item["acertos_14"]
                + item["acertos_15"]
            ) / qtd
        )

        item["taxa_12"] = item["acertos_12"] / qtd
        item["taxa_13"] = item["acertos_13"] / qtd
        item["taxa_14"] = item["acertos_14"] / qtd
        item["taxa_15"] = item["acertos_15"] / qtd

        item["score_ponderado"] = (
            item["score_ponderado"] / qtd
        )

        (
            supabase
            .table("palpites_resultados_reais")
            .upsert(
                item,
                on_conflict="data_referencia,versao_gerador,concurso_inicio"
            )
            .execute()
        )

    print("✅ Histórico reconstruído")


if __name__ == "__main__":
    main()
