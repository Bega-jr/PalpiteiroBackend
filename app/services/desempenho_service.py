from app.services.supabase_service import get_supabase

def obter_desempenho_gerador(
    ano: int,
    tipo_palpite: str,
    versao_gerador: str
):
    supabase = get_supabase()

    # Primeiro concurso do ano de 2026
    inicio_ano = 3576

    # Busca os registros do backtest
    resp = (
        supabase
        .table("backtest_resultados")
        .select(
            "concurso_inicio, concurso_fim, total_concursos, "
            "acertos_11, acertos_12, acertos_13, acertos_14, acertos_15"
        )
        .eq("tipo_palpite", tipo_palpite)
        .eq("versao_gerador", versao_gerador)
        .execute()
    )

    if not resp.data:
        return None

    resumo = {
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
    }

    total_concursos = 0

    for r in resp.data:
        c_inicio = r.get("concurso_inicio")
        c_fim = r.get("concurso_fim")
        total = r.get("total_concursos", 0)

        # Determina quantos concursos desse registro entram no ano de 2026
        concursos_validos = max(0, c_fim - max(c_inicio, inicio_ano) + 1)
        if concursos_validos <= 0:
            continue

        # Ajuste proporcional dos acertos
        fator = concursos_validos / total if total > 0 else 0

        resumo["11"] += int(r.get("acertos_11", 0) * fator)
        resumo["12"] += int(r.get("acertos_12", 0) * fator)
        resumo["13"] += int(r.get("acertos_13", 0) * fator)
        resumo["14"] += int(r.get("acertos_14", 0) * fator)
        resumo["15"] += int(r.get("acertos_15", 0) * fator)

        total_concursos += concursos_validos

    return {
        "resumo": resumo,
        "total_concursos": total_concursos
    }
