import json
from app.services.supabase_service import get_supabase


def conferir_jogos_do_dia():
    """
    Faz conferência histórica de todos concursos
    e grava performance real por versão do gerador.
    """

    supabase = get_supabase()

    print("🚀 Iniciando conferência histórica...")

    # resultados oficiais
    res_oficiais = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso, dezenas, data")
        .order("concurso", desc=True)
        .execute()
    )

    if not res_oficiais.data:
        return "Nenhum concurso oficial encontrado."

    concursos_processados = 0

    for sorteio in res_oficiais.data:

        concurso_id = sorteio["concurso"]
        data_ref = sorteio["data"]

        dezenas_sorteadas = set(
            map(
                int,
                sorteio["dezenas"]
            )
        )

        # busca palpites daquele dia
        palpites_res = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", data_ref)
            .execute()
        )

        if not palpites_res.data:
            continue

        resumo = {}

        # ==========================
        # PROCESSA PALPITES
        # ==========================
        for p in palpites_res.data:

            try:

                raw_nums = p.get("numeros")

                if isinstance(raw_nums, str):

                    clean = (
                        raw_nums
                        .strip('"')
                        .replace("\\", "")
                    )

                    numeros_lista = json.loads(clean)

                else:
                    numeros_lista = raw_nums

                numeros_palpite = set(
                    map(int, numeros_lista)
                )

                acertos = len(
                    numeros_palpite &
                    dezenas_sorteadas
                )

                tipo = p.get(
                    "tipo",
                    "fixo"
                )

                versao = p.get(
                    "versao_gerador",
                    "desconhecida"
                )

                chave = (
                    tipo,
                    versao
                )

                if chave not in resumo:

                    resumo[chave] = {
                        "11": 0,
                        "12": 0,
                        "13": 0,
                        "14": 0,
                        "15": 0
                    }

                if acertos >= 11:

                    resumo[chave][
                        str(acertos)
                    ] += 1

            except Exception as e:

                print(
                    f"Erro processando palpite: {e}"
                )

                continue

        # ==========================
        # SALVA RESULTADOS
        # ==========================
        for (
            tipo,
            versao
        ), counts in resumo.items():

            # remove apenas registro idêntico
            (
                supabase
                .table("palpites_resultados_reais")
                .delete()
                .eq("concurso", concurso_id)
                .eq("tipo_palpite", tipo)
                .eq("versao_gerador", versao)
                .execute()
            )

            payload = {

                "concurso": concurso_id,

                "tipo_palpite": tipo,

                "versao_gerador": versao,

                "acertos_11": counts["11"],
                "acertos_12": counts["12"],
                "acertos_13": counts["13"],
                "acertos_14": counts["14"],
                "acertos_15": counts["15"],

                "total_concursos": 1,

                "data_referencia": data_ref
            }

            (
                supabase
                .table("palpites_resultados_reais")
                .insert(payload)
                .execute()
            )

        concursos_processados += 1

        print(
            f"✅ Concurso {concurso_id} processado"
        )

    print(
        f"🏁 Finalizado: "
        f"{concursos_processados} concursos"
    )

    return (
        f"{concursos_processados} concursos processados."
    )

