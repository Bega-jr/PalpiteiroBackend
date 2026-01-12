import json
from app.services.supabase_service import get_supabase

def processar_premios(acertos: int) -> float:
    """Retorna o valor do prêmio baseado nos acertos da Lotofácil (valores 2026)."""
    premios = {
        11: 7.0,
        12: 14.0,
        13: 35.0,
        14: 1500.0,
        15: 1800000.0
    }
    return premios.get(acertos, 0.0)

def conferir_jogos_do_dia():
    """
    Busca o último resultado em lotofacil_concursos e confere:
    1. Jogos do sistema (palpites_validos)
    2. Jogos dos usuários (saved_games)
    Resultados do sistema são salvos em palpites_resultados_reais.
    """
    supabase = get_supabase()

    # 1️⃣ Último resultado oficial
    res_oficial = supabase.table("lotofacil_concursos")\
        .select("*")\
        .order("concurso", desc=True)\
        .limit(1).execute()

    if not res_oficial.data:
        return "Erro: Nenhum resultado oficial encontrado."

    sorteio = res_oficial.data[0]
    concurso_atual = sorteio['concurso']
    dezenas_sorteadas = set(map(int, sorteio['dezenas']))

    # 2️⃣ Conferência de palpites do sistema
    palpites_res = supabase.table("palpites_validos")\
        .select("*")\
        .eq("data_referencia", sorteio['data'])\
        .execute()

    if palpites_res.data:
        resumo_resultados = {}

        for p in palpites_res.data:
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

        # Salva na tabela palpites_resultados_reais
        for tipo, counts in resumo_resultados.items():
            # Evita duplicidade para o mesmo concurso e tipo
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
                "data_referencia": sorteio['data']
            }).execute()

    # 3️⃣ Conferência de jogos dos usuários
    jogos_usuarios = supabase.table("saved_games")\
        .select("*")\
        .eq("concurso_alvo", concurso_atual)\
        .eq("conferido", False).execute()

    total_usuarios_conferidos = 0
    if jogos_usuarios.data:
        for jogo in jogos_usuarios.data:
            dezenas_jogo = set(map(int, jogo['numeros']))
            acertos = len(dezenas_jogo & dezenas_sorteadas)
            valor_premio = processar_premios(acertos)

            supabase.table("saved_games").update({
                "acertos": acertos,
                "valor_premio": valor_premio,
                "conferido": True
            }).eq("id", jogo["id"]).execute()
            total_usuarios_conferidos += 1

    return f"Sucesso: Concurso {concurso_atual} conferido. Sistema e {total_usuarios_conferidos} jogos de usuários atualizados."


