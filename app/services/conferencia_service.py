import json
from app.services.supabase_service import get_supabase

def conferir_jogos_do_dia():
    """
    Faz conferência histórica otimizada de todos os concursos
    e grava a performance real em lote (upsert) mapeando concurso_inicio.
    """
    supabase = get_supabase()
    print("🚀 Iniciando conferência histórica...")

    # 1. Busca todos os resultados oficiais de uma vez
    res_oficiais = (
        supabase.table("lotofacil_concursos")
        .select("concurso, dezenas, data")
        .order("concurso", desc=True)
        .execute()
    )

    if not res_oficiais.data:
        print("❌ Nenhum concurso oficial encontrado")
        return "Nenhum concurso oficial encontrado."

    total_concursos = 0
    total_palpites = 0
    payloads_para_salvar = []

    for sorteio in res_oficiais.data:
        try:
            concurso_id = sorteio["concurso"]
            data_ref = sorteio["data"]
            dezenas_sorteadas = set(map(int, sorteio["dezenas"]))
        except Exception as e:
            print(f"❌ Erro no concurso {sorteio.get('concurso')}: {e}")
            continue

        # 2. Busca palpites específicos da data de referência
        palpites_res = (
            supabase.table("palpites_validos")
            .select("numeros, tipo, versao_gerador")
            .eq("data_referencia", data_ref)
            .execute()
        )

        if not p_data := palpites_res.data:
            continue

        resumo = {}

        # 3. Processamento em memória rápido usando Sets
        for p in p_data:
            try:
                raw_nums = p.get("numeros")
                if not raw_nums:
                    continue

                # Normalização segura de JSON
                if isinstance(raw_nums, str):
                    numeros_lista = json.loads(raw_nums.strip('"').replace("\\", ""))
                else:
                    numeros_lista = raw_nums

                if len(numeros_lista) != 15:
                    continue

                numeros_palpite = set(map(int, numeros_lista))
                if len(numeros_palpite) != 15:
                    continue

                acertos = len(numeros_palpite & dezenas_sorteadas)
                tipo = p.get("tipo", "fixo")
                versao = p.get("versao_gerador", "legacy")
                chave = (tipo, versao)

                if chave not in resumo:
                    resumo[chave] = {"11": 0, "12": 0, "13": 0, "14": 0, "15": 0}

                if acertos >= 11:
                    resumo[chave][str(acertos)] += 1

                total_palpites += 1
            except Exception as e:
                print(f"⚠️ Erro no palpite: {e}")
                continue

        # 4. Prepara dados para Upsert em Lote (Usando concurso_inicio)
        for (tipo, versao), counts in resumo.items():
            payloads_para_salvar.append({
                "concurso_inicio": concurso_id,  # 👈 Ajustado para bater com a unique constraint do banco
                "tipo_palpite": tipo,
                "versao_gerador": versao,
                "acertos_11": counts["11"],
                "acertos_12": counts["12"],
                "acertos_13": counts["13"],
                "acertos_14": counts["14"],
                "acertos_15": counts["15"],
                "total_concursos": 1,
                "data_referencia": data_ref
            })

        total_concursos += 1

    # 5. Executa a persistência em lote usando o Upsert nativo
    if payloads_para_salvar:
        try:
            print(f"💾 Salvando {len(payloads_para_salvar)} registros de performance...")
            supabase.table("palpites_resultados_reais").upsert(payloads_para_salvar).execute()
        except Exception as e:
            print(f"❌ Erro fatal no Upsert: {e}")

    print("\n🏁 Conferência concluída")
    print(f"📌 Concursos processados: {total_concursos}")
    print(f"📌 Palpites validados: {total_palpites}")

    return f"{total_concursos} concursos | {total_palpites} palpites"
