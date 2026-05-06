import sys
import json
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from app.services.supabase_service import get_supabase


def extrair_estrutura(nums):
    return {
        "soma_faixa": int(round(sum(nums) / 10) * 10),
        "pares": sum(1 for n in nums if n % 2 == 0),
        "primos": sum(
            1 for n in nums
            if n in {2, 3, 5, 7, 11, 13, 17, 19, 23}
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


def parse_numeros(valor):
    try:
        if isinstance(valor, list):
            return [int(x) for x in valor]

        if isinstance(valor, str):
            return [int(x) for x in json.loads(valor)]

    except Exception:
        return None

    return None


def obter_versao(p):
    metricas = p.get("metricas") or {}

    return (
        p.get("versao_gerador")
        or metricas.get("versao")
        or "legacy"
    )


def obter_resultado_oficial(supabase, concurso):
    resultado = (
        supabase
        .table("lotofacil_concursos")
        .select("dezenas")
        .eq("concurso", concurso)
        .limit(1)
        .execute()
        .data
    )

    if not resultado:
        return None

    dezenas_raw = resultado[0]["dezenas"]

    if isinstance(dezenas_raw, str):
        return set(json.loads(dezenas_raw))

    return set(dezenas_raw)


def main():

    supabase = get_supabase()

    print("🏁 Conferindo resultados...")

    palpites = (
        supabase
        .table("palpites_validos")
        .select("*")
        .is_("acertos", None)
        .execute()
        .data
    )

    if not palpites:
        print("⚠️ Nada para conferir")
        return

    print(f"📌 {len(palpites)} palpites pendentes")

    processados = 0

    for p in palpites:

        try:

            numeros = parse_numeros(
                p["numeros"]
            )

            if not numeros:
                continue

            concurso_ref = p["concurso_referencia"]

            dezenas_oficiais = obter_resultado_oficial(
                supabase,
                concurso_ref
            )

            if not dezenas_oficiais:
                print(
                    f"⚠️ Concurso {concurso_ref} ainda não existe"
                )
                continue

            acertos = len(
                set(numeros) & dezenas_oficiais
            )

            estrutura = extrair_estrutura(
                numeros
            )

            peso = peso_acerto(
                acertos
            )

            versao = obter_versao(p)

            # Atualiza palpite
            (
                supabase
                .table("palpites_validos")
                .update({
                    "acertos": acertos
                })
                .eq("id", p["id"])
                .execute()
            )

            # Atualiza memória
            memoria_payload = {
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
                    memoria_payload,
                    on_conflict="soma_faixa,pares,primos,linhas"
                )
                .execute()
            )

            # Verifica se já existe resultado
            existe = (
                supabase
                .table("palpites_resultados_reais")
                .select("id")
                .eq("data_referencia", p["data_referencia"])
                .eq("versao_gerador", versao)
                .eq("concurso_inicio", concurso_ref)
                .limit(1)
                .execute()
                .data
            )

            if not existe:

                resultado_payload = {
                    "data_referencia": p["data_referencia"],
                    "concurso_inicio": concurso_ref,
                    "concurso_fim": concurso_ref,
                    "versao_gerador": versao,

                    "qtd_palpites": 1,

                    "acertos_11": 1 if acertos == 11 else 0,
                    "acertos_12": 1 if acertos == 12 else 0,
                    "acertos_13": 1 if acertos == 13 else 0,
                    "acertos_14": 1 if acertos == 14 else 0,
                    "acertos_15": 1 if acertos == 15 else 0,

                    "eficiencia": 1 if acertos >= 11 else 0
                }

                (
                    supabase
                    .table("palpites_resultados_reais")
                    .insert(resultado_payload)
                    .execute()
                )

            print(
                f"✅ Concurso {concurso_ref} | {acertos} acertos"
            )

            processados += 1

        except Exception as e:

            print(
                f"❌ Erro no palpite {p.get('id')}: {e}"
            )

    print(
        f"✅ {processados} palpites conferidos"
    )


if __name__ == "__main__":
    main()
