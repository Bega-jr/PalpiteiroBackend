from app.services.supabase_service import get_supabase

def obter_desempenho_gerador(
    ano: int,
    tipo_palpite: str,
    versao_gerador: str
):
    supabase = get_supabase()

    # O concurso 3576 marca o início de 2026
    inicio_concurso_ano = {
        2026: 3576
    }
    
    concurso_minimo = inicio_concurso_ano.get(ano, 0)

    # Busca registros que começaram a partir do concurso inicial do ano
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

    # Acumuladores inteiros para contagem absoluta
    resumo = {
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
    }
    total_concursos_processados = 0

    for r in resp.data:
        # Soma os acertos de cada categoria de forma independente
        resumo["11"] += int(r.get("acertos_11", 0))
        resumo["12"] += int(r.get("acertos_12", 0))
        resumo["13"] += int(r.get("acertos_13", 0))
        resumo["14"] += int(r.get("acertos_14", 0))
        resumo["15"] += int(r.get("acertos_15", 0))

        # Calcula a abrangência de concursos deste registro específico
        c_inicio = r.get("concurso_inicio", 0)
        c_fim = r.get("concurso_fim", 0)
        total_concursos_processados += (c_fim - c_inicio + 1)

    return {
        "resumo": resumo,
        "total_concursos": total_concursos_processados,
        "ano_referencia": ano
    }

