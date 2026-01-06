from datetime import date
from app.core.supabase import supabase


def _hoje_iso():
    return date.today().isoformat()


# =====================================================
# PALPITES DO DIA
# =====================================================

def listar_palpites_hoje():
    """
    Retorna todos os palpites válidos do dia.
    Nunca lança exceção.
    """
    hoje = _hoje_iso()

    try:
        response = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", hoje)
            .order("indice_palpite")
            .execute()
        )

        return response.data or []

    except Exception as e:
        print(f"❌ Erro ao listar palpites do dia: {e}")
        return []


def carregar_palpite_fixo():
    """
    Retorna apenas os números do palpite fixo do dia.
    Retorna None se não existir.
    """
    hoje = _hoje_iso()

    try:
        response = (
            supabase
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

    except Exception as e:
        print(f"❌ Erro ao carregar palpite fixo: {e}")
        return None
