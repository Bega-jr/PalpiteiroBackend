from app.services.supabase_service import get_supabase

def carregar_estatisticas_diarias():
    """
    Busca o último snapshot diário de estatísticas.
    """

    response = (
        get_supabase()
        .table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0] # Retorna o primeiro item da lista ou None
