import json
from app.services.supabase_service import get_supabase

def processar_premios(acertos: int) -> float:
    premios = {11: 7.0, 12: 14.0, 13: 35.0, 14: 1500.0, 15: 1800000.0}
    return premios.get(acertos, 0.0)

def conferir_jogos_do_dia():
    supabase = get_supabase()

    # 1️⃣ Busca todas as datas únicas que possuem palpites salvos
    # Isso permite conferir hoje, ontem ou qualquer data pendente
    palpites_query = supabase.table("palpites_validos").select("data_referencia").execute()
    if not palpites_query.data:
        return "Nenhum palpite encontrado para processar."

    # Remove duplicatas de datas
    datas_para_conferir = sorted(list(set(p['data_referencia'] for p in palpites_query.data)))
    
    total_concursos_processados = 0

    for data_ref in datas_para_conferir:
        # 2️⃣ Busca o resultado oficial para esta data específica
        res_oficial = supabase.table("lotofacil_concursos")\
            .select("*")\
            .eq("data", data_ref)\
            .execute()

        if not res_oficial.data:
            print(f"Aviso: Resultado para a data {data_ref} ainda não está no banco. Pulando...")
            continue

        sorteio = res_oficial.data[0]
        concurso_atual = sorteio['concurso']
        dezenas_sorteadas = set(map(int, sorteio['dezenas']))

        # 3️⃣ Busca todos os palpites do sistema para esta data
        palpites_res = supabase.table("palpites_validos")\
            .select("*")\
            .eq("data_referencia", data_ref)\
            .execute()

        if palpites_res.data:
            resumo_resultados = {}
            for p in palpites_res.data:
                # Tratamento de aspas e JSON
                raw_nums = p.get("numeros")
                if isinstance(raw_nums, str):
                    clean_nums = raw_nums.strip('"').replace('\\', '')
                    numeros_lista = json.loads(clean_nums)
                else:
                    numeros_lista = raw_nums

                numeros_palpite = set(map(int, numeros_lista))
                tipo = p.get("tipo", "fixo")
                acertos = len(numeros_palpite & dezenas_sorteadas)

                if tipo not in resumo_resultados:
                    resumo_resultados[tipo] = {"11":0, "12":0, "13":0, "14":0, "15":0}

                if acertos >= 11:
                    resumo_resultados[tipo][str(acertos)] += 1

            # 4️⃣ Salva/Atualiza na tabela palpites_resultados_reais
            for tipo, counts in resumo_resultados.items():
                # Upsert: Deleta o antigo se existir e insere o novo (evita duplicidade)
                supabase.table("palpites_resultados_reais").delete()\
                    .eq("concurso", concurso_atual)\
                    .eq("tipo_palpite", tipo).execute()

                supabase.table("palpites_resultados_reais").insert({
                    "concurso": concurso_atual,
                    "tipo_palpite": tipo,
                    "versao_gerador": "v1.0",
                    "acertos_11": counts["11"],
                    "acertos_12": counts["12"],
                    "acertos_13": counts["13"],
                    "acertos_14": counts["14"],
                    "acertos_15": counts["15"],
                    "total_concursos": 1,
                    "data_referencia": data_ref
                }).execute()
            
            total_concursos_processados += 1

    # 5️⃣ Conferência de usuários (mantida para o concurso mais recente)
    # Aqui você pode manter a lógica anterior ou também iterar por datas
    return f"Sucesso: {total_concursos_processados} datas de sorteios processadas."

