import json
from typing import List, Dict, Any
from .supabase_service import get_supabase

# Versão simplificada para teste (retorna dados brutos)
def obter_palpite_fixo_publico() -> Dict[str, Any] | None:
    try:
        supabase = get_supabase()
        # Busca o registro mais recente pelo score, sem filtros complexos
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )
        return resp.data[0] if resp.data else None
    except Exception as e:
        print(f"❌ Erro service fixo: {repr(e)}")
        return {"erro": str(e)}

def obter_palpites_estatisticos_publico() -> List[Dict[str, Any]]:
    try:
        supabase = get_supabase()
        # Busca os últimos 10 registros sem tratar JSON ou Arrays
        resp = (
            supabase
            .table("palpites_validos")
            .select("*")
            .order("data_referencia", desc=True)
            .limit(10)
            .execute()
        )
        return resp.data if resp.data else []
    except Exception as e:
        print(f"❌ Erro service estatísticos: {repr(e)}")
        return [{"erro": str(e)}]

