from app.services.supabase_service import get_supabase
from datetime import date

def obter_desempenho_gerador(
    ano: int,
    tipo_palpite: str | None = None,
    versao_gerador: str | None = None
):
    supabase = get_supabase()

    # Filtro por ano usando data_referencia (CORRETO)
    data_inicio = f"{ano}-01-01"
    data_fim = f"{ano}-12-31"

    query = (
        supabase
        .table("palpites_resultados_reais")
        .select(
            "concurso_inicio, concurso_fim, "
            "acertos_11, acertos_12, acertos_13, acertos_14, acertos_15"
        )
        .gte("data_referencia", data_inicio)
        .lte("data_referencia", data_fim)
    )

    # Filtros opcionais (NÃO travam o card)
    if tipo_palpite:
        query = query.eq("tipo_palpite", tipo_palpite)

    if versao_gerador:
        query = query.eq("versao_gerador", versao_gerador)

    resp = query.execute()

    if not resp.data:
        return {
            "resumo": {"11": 0, "12": 0, "13": 0, "14": 0, "15": 0},
            "total_concursos": 0,
            "ano_referencia": ano
        }

    resumo = {"11": 0, "12": 0, "13": 0, "14": 0, "15": 0}
    total_concursos = 0

    for r in resp.data:
        resumo["11"] += int(r.get("acertos_11", 0))
        resumo["12"] += int(r.get("acertos_12", 0))
        resumo["13"] += int(r.get("acertos_13", 0))
        resumo["14"] += int(r.get("acertos_14", 0))
        resumo["15"] += int(r.get("acertos_15", 0))

        inicio = r.get("concurso_inicio", 0)
        fim = r.get("concurso_fim", 0)
        if inicio and fim:
            total_concursos += (fim - inicio + 1)

    return {
        "resumo": resumo,
        "total_concursos": total_concursos,
        "ano_referencia": ano
    }

