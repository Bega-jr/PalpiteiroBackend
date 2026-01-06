# Ajuste na importação para usar o serviço correto
from app.services.supabase_service import get_supabase

# Inicializa o cliente Supabase
supabase = get_supabase()

def carregar_estatisticas_diarias():
    """
    Busca o último snapshot diário de estatísticas.
    """

    response = (
        supabase
        .table("estatisticas_diarias_v2")
        .select("*")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
    )

    if not response.data:
        return None

    return response.data[0] # Retorna o primeiro item da lista ou None
