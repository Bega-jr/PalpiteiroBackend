from datetime import date

from app.services.supabase_service import get_supabase

def _hoje_iso():
    return date.today().isoformat()


# =====================================================
# PALPITES DO DIA
# =====================================================

def listar_palpites_hoje():
    """
    Retorna todos os palpites válidos do dia.
    """
    hoje = _hoje_iso()

    response = (
        get_supabase()
        .table("palpites_validos")
        .select("*")
        .eq("data_referencia", hoje)
        .order("indice_palpite")
        .execute()
    )

    return response.data or []

def carregar_palpite_fixo():
    """
    Retorna apenas os números do palpite fixo do dia.
    Retorna None se não existir.
    """
    hoje = _hoje_iso()

    response = (
        get_supabase()
        .table("palpites_validos")
        .select("numeros")
        .eq("data_referencia", hoje)
        .eq("indice_palpite", 1)
        .limit(1)
        .execute()
    )

    dados = response.data or []
    if not dados:
        return None

    return dados[0].get("numeros")
