# app/services/repeticao_service.py

from app.services.supabase_service import get_supabase

def obter_ultimos_concursos(qtd=3):
    supabase = get_supabase()

    concursos = (
        supabase.table("historico_resultados")
        .select("numeros")
        .order("concurso", desc=True)
        .limit(qtd)
        .execute()
    ).data

    return [set(c["numeros"]) for c in concursos] if concursos else []


def score_repeticao(nums, ultimos_concursos):
    """
    Retorna score entre 0 e 1
    """
    if not ultimos_concursos:
        return 1.0

    repeticoes = [
        len(set(nums) & concurso)
        for concurso in ultimos_concursos
    ]

    score = 1.0

    # Último concurso
    if repeticoes[0] < 6 or repeticoes[0] > 11:
        score *= 0.4

    # Últimos 2
    if len(repeticoes) > 1 and (repeticoes[1] < 7 or repeticoes[1] > 12):
        score *= 0.6

    # Últimos 3
    if len(repeticoes) > 2 and (repeticoes[2] < 8 or repeticoes[2] > 13):
        score *= 0.7

    return round(score, 3)
