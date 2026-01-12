from app.services.supabase_service import get_supabase


def obter_desempenho_gerador(
    ano: int,
    tipo_palpite: str,
    versao_gerador: str
):
    supabase = get_supabase()

    resp = (
        supabase
        .table("backtest_resultados")
        .select(
            "acertos_11, acertos_12, acertos_13, acertos_14, acertos_15, total_concursos"
        )
        .eq("ano", ano)
        .eq("tipo_palpite", tipo_palpite)
        .eq("versao_gerador", versao_gerador)
        .execute()
    )

    if not resp.data:
        return None

    # soma defensiva (permite múltiplos registros no futuro)
    resumo = {
        "11": 0,
        "12": 0,
        "13": 0,
        "14": 0,
        "15": 0,
    }

    total_concursos = 0

    for r in resp.data:
        resumo["11"] += r.get("acertos_11", 0)
        resumo["12"] += r.get("acertos_12", 0)
        resumo["13"] += r.get("acertos_13", 0)
        resumo["14"] += r.get("acertos_14", 0)
        resumo["15"] += r.get("acertos_15", 0)
        total_concursos += r.get("total_concursos", 0)

    return {
        "resumo": resumo,
        "total_concursos": total_concursos
    }
