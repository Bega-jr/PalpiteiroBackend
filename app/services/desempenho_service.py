from app.services.supabase_service import get_supabase

def obter_desempenho_gerador(
    ano: int,
    tipo_palpite: str,
    versao_gerador: str
):
    supabase = get_supabase()

    # Mapeamento de início de concursos por ano
    # Se ano for 2026, inicia em 3576. Caso contrário, busca do zero ou outra regra.
    inicio_ano = 3576 if ano == 2026 else 0

    # Busca apenas os registros que tenham alguma intersecção com o ano solicitado
    resp = (
        supabase
        .table("backtest_resultados")
        .select(
            "concurso_inicio, concurso_fim, total_concursos, "
            "acertos_11, acertos_12, acertos_13, acertos_14, acertos_15"
        )
        .eq("tipo_palpite", tipo_palpite)
        .eq("versao_gerador", versao_gerador)
        .gte("concurso_fim", inicio_ano) # Garante que terminou dentro ou após o início do ano
        .execute()
    )

    if not resp.data:
        return None

    # Usamos floats para o cálculo inicial para não perder precisão com int() precoce
    resumo_float = {
        "11": 0.0,
        "12": 0.0,
        "13": 0.0,
        "14": 0.0,
        "15": 0.0,
    }

    total_concursos_acumulado = 0

    for r in resp.data:
        c_inicio = r.get("concurso_inicio", 0)
        c_fim = r.get("concurso_fim", 0)
        
        # O total_concursos real do registro (baseado nos IDs)
        # Usamos isso para o fator, caso o campo 'total_concursos' do banco esteja inconsistente
        total_real_no_registro = (c_fim - c_inicio + 1)
        
        # Determina quantos concursos deste registro pertencem ao ano de 2026 em diante
        # Ex: Se começou em 3570 e o ano inicia em 3576, pega de 3576 até o fim
        concursos_validos_no_ano = max(0, c_fim - max(c_inicio, inicio_ano) + 1)
        
        if concursos_validos_no_ano <= 0:
            continue

        # Calcula o fator de proporção: 
        # (Concursos que pertencem a 2026) / (Total de concursos que o registro abrange)
        fator = concursos_validos_no_ano / total_real_no_registro if total_real_no_registro > 0 else 0

        # Acumula os valores como float
        resumo_float["11"] += r.get("acertos_11", 0) * fator
        resumo_float["12"] += r.get("acertos_12", 0) * fator
        resumo_float["13"] += r.get("acertos_13", 0) * fator
        resumo_float["14"] += r.get("acertos_14", 0) * fator
        resumo_float["15"] += r.get("acertos_15", 0) * fator

        total_concursos_acumulado += concursos_validos_no_ano

    # Retorna os valores arredondados para o inteiro mais próximo
    return {
        "resumo": {k: round(v) for k, v in resumo_float.items()},
        "total_concursos": total_concursos_acumulado,
        "ano_referencia": ano
    }

