from .supabase_service import get_supabase

def obter_palpites_estatisticos_publico():
    try:
        supabase = get_supabase()
        # Removido o .order() e .limit() para o teste mais simples possível
        query = supabase.table("palpites_validos").select("*").execute()
        
        # O Supabase SDK retorna .data (sucesso) e pode conter informações de erro internamente
        return {
            "dados": query.data,
            "total_encontrado": len(query.data) if query.data else 0
        }
    except Exception as e:
        # Retorna o erro exato (ex: "42501: permission denied" ou "Invalid API Key")
        return {"erro_sistema": str(e)}

def obter_palpite_fixo_publico():
    # Para teste rápido, use a mesma lógica de cima
    return obter_palpites_estatisticos_publico()
