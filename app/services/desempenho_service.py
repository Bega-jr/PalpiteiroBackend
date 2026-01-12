from app.services.supabase_service import get_supabase

def obter_desempenho_gerador(
    ano: int,
    tipo_palpite: str,
    versao_gerador: str
):
    supabase = get_supabase()

    # Define o primeiro concurso de 2026
    # Se no futuro houver outros anos, basta adicionar ao dicionário
    inicio_concurso_ano = {
        2026: 3576
    }
    
    concurso_minimo = inicio_concurso_ano.get(ano, 0)

    # Busca os registros
    # Filtramos para pegar apenas registros que ocorreram de 3576 para frente
    resp = (
        supabase
        .table("backtest_resultados")
        .select(
            "concurso_inicio, concurso_fim, "
            "acertos_11, acertos_12, acertos_13, acertos_14, acertos_15"
        )
        .eq("tipo_palpite", tipo_palpite)
        .eq("versao_gerador", versao_gerador)
        .gte("concurso_inicio", concurso_minimo) 
        .execute()
    )

    if not resp.data:
        return None

    # Inicializa contadores como inteiros
    resumo = {
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
    }
    total_concursos = 0

    for r in resp.data:
        # Soma direta dos acertos (sem divisões ou fatores)
        resumo["11"] += r.get("acertos_11", 0)
        resumo["12"] += r.get("acertos_12", 0)
        resumo["13"] += r.get("acertos_13", 0)
        resumo["14"] += r.get("acertos_14", 0)
        resumo["15"] += r.get("acertos_15", 0)

        # Calcula a quantidade de concursos processados nesta linha
        c_inicio = r.get("concurso_inicio")
        c_fim = r.get("concurso_fim")
        total_concursos += (c_fim - c_inicio + 1)

    return {
        "resumo": resumo,
        "total_concursos": total_concursos,
        "ano": ano
    }

