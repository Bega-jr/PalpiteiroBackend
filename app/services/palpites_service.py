from datetime import date
from app.services.supabase_service import get_supabase

def obter_palpite_fixo_publico():
    """Busca o registro de índice 0 da data mais recente."""
    try:
        supabase = get_supabase()
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("indice_palpite", 0)
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        # Se resp.data for uma lista com itens, retornamos o primeiro dicionário puro
        if resp.data and len(resp.data) > 0:
            return resp.data[0] 
        return None
    except Exception as e:
        print(f"❌ Erro Service Fixo: {repr(e)}")
        return None

def obter_palpites_estatisticos_publico():
    """Busca todos os registros (exceto índice 0) da data mais recente."""
    try:
        supabase = get_supabase()
        # 1. Pega a data mais recente que tem algum dado
        data_resp = supabase.table("palpites_validos").select("data_referencia").order("data_referencia", desc=True).limit(1).execute()
        
        if not data_resp.data:
            return []
            
        ultima_data = data_resp.data[0]["data_referencia"]

        # 2. Busca os palpites dessa data
        resp = (
            supabase.table("palpites_validos")
            .select("*")
            .eq("data_referencia", ultima_data)
            .gt("indice_palpite", 0)
            .order("indice_palpite", desc=False)
            .execute()
        )
        return resp.data or []
    except Exception as e:
        print(f"❌ Erro Service Estatisticos: {repr(e)}")
        return []

