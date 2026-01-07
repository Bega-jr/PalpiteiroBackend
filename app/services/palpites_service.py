from typing import List, Dict, Optional
from app.services.supabase_service import get_supabase


def obter_palpite_fixo_publico() -> Optional[Dict]:
    """
    Retorna o palpite fixo (indice_palpite = 0)
    da data mais recente disponível no banco.
    """
    try:
        supabase = get_supabase()

        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("indice_palpite", 0)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        if resp.data and len(resp.data) > 0:
            return resp.data[0]

        return None

    except Exception as e:
        print(f"❌ Erro obter_palpite_fixo_publico: {repr(e)}")
        return None


def obter_palpites_estatisticos_publico() -> List[Dict]:
    """
    Retorna todos os palpites estatísticos
    (indice_palpite > 0) da data mais recente disponível.
    """
    try:
        supabase = get_supabase()

        # 1️⃣ Descobre a data mais recente existente
        data_resp = (
            supabase
            .table("palpites_validos")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

        if not data_resp.data:
            return []

        ultima_data = data_resp.data[0]["data_referencia"]

        # 2️⃣ Busca todos os palpites dessa data
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .eq("data_referencia", ultima_data)
            .gt("indice_palpite", 0)
            .order("indice_palpite")
            .execute()
        )

        return resp.data or []

    except Exception as e:
        print(f"❌ Erro obter_palpites_estatisticos_publico: {repr(e)}")
        return []
