import json
from app.services.supabase_service import get_supabase

def conferir_jogos_do_dia():
    """
    Realiza a conferência retroativa de TODOS os concursos presentes no banco
    que possuam palpites correspondentes na tabela palpites_validos.
    """
    supabase = get_supabase()

    # 1️⃣ Busca todos os resultados oficiais disponíveis
    res_oficiais = supabase.table("lotofacil_concursos")\
        .select("concurso, dezenas, data")\
        .order("concurso", desc=True)\
        .execute()

    if not res_oficiais.data:
        return "Erro: Nenhumm resultado oficial encontrado para conferência histórica."

    concursos_processados = 0

    # 2️⃣ Itera sobre cada concurso oficial do banco
    for sorteio in res_oficiais.data:
        concurso_id = sorteio['concurso']
        data_ref = sorteio['data']
        dezenas_sorteadas = set(map(int, sorteio['dezenas']))

        # 3️⃣ Busca se existem palpites do sistema para ESTA data específica
        palpites_res = supabase.table("palpites_validos")\
            .select("*")\
            .eq("data_referencia", data_ref)\
            .execute()

        # Se não houver palpites para esta data, pula para o próximo concurso
        if not palpites_res.data:
            continue

        resumo_resultados = {}
        for p in palpites_res.data:
            # Tratamento de aspas duplas e conversão JSON
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

        # 4️⃣ Grava ou atualiza os resultados na tabela de performance
        for tipo, counts in resumo_resultados.items():
            # Usamos o RPC ou delete/insert para garantir que a linha seja atualizada
            supabase.table("palpites_resultados_reais").delete()\
                .eq("concurso", concurso_id)\
                .eq("tipo_palpite", tipo).execute()

            supabase.table("palpites_resultados_reais").insert({
                "concurso": concurso_id,
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
        
        concursos_processados += 1

    return f"Carga histórica concluída: {concursos_processados} concursos conferidos e populados."


