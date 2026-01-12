from app.services.supabase_service import get_supabase
from app.services.palpites_service import _gerar_palpites_core


def executar_backtest(
    concurso_inicio: int,
    concurso_fim: int,
    qtd_palpites: int = 7
):
    supabase = get_supabase()

    concursos = (
        supabase
        .table("lotofacil_concursos")
        .select("concurso, numeros")
        .gte("concurso", concurso_inicio)
        .lte("concurso", concurso_fim)
        .order("concurso")
        .execute()
        .data
    )

    if not concursos:
        raise Exception("Concursos não encontrados")

    estatisticas = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, score, frequencia, atraso, tendencia")
        .execute()
        .data
    )

    resumo = {
        "total_concursos": 0,
        "media_acertos": 0,
        "melhor_acerto": 0,
        "acertos_11+": 0,
        "acertos_12+": 0,
        "acertos_13+": 0
    }

    total_acertos = 0

    for conc in concursos:
        resultado = conc["numeros"]

        palpites = _gerar_palpites_core(
            estatisticas=estatisticas,
            qtd_palpites=qtd_palpites,
            persistir=False
        )

        melhor = 0
        for p in palpites:
            acertos = len(set(p) & set(resultado))
            melhor = max(melhor, acertos)

        resumo["total_concursos"] += 1
        total_acertos += melhor
        resumo["melhor_acerto"] = max(resumo["melhor_acerto"], melhor)

        if melhor >= 11:
            resumo["acertos_11+"] += 1
        if melhor >= 12:
            resumo["acertos_12+"] += 1
        if melhor >= 13:
            resumo["acertos_13+"] += 1

    resumo["media_acertos"] = round(
        total_acertos / resumo["total_concursos"], 2
    )

    return resumo

