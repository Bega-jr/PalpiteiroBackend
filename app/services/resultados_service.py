import os
from typing import List, Dict
from supabase import create_client, Client

# Substitua pelas suas variáveis de ambiente ou valores reais
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Ou anon key

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_resultados_supabase(page: int = 1, limit: int = 10) -> Dict:
    """Busca resultados paginados do Supabase"""
    try:
        # Cálculo de offset para paginação
        start = (page - 1) * limit
        end = start + limit - 1

        response = supabase.table("lotofacil_concursos") \
            .select("*", count="exact") \
            .order("concurso", descending=True) \
            .range(start, end) \
            .execute()

        return {
            "resultados": response.data,
            "total": response.count
        }
    except Exception as e:
        print(f"Erro Supabase: {e}")
        return {"resultados": [], "total": 0}

def fetch_concurso_unico_supabase(numero: int) -> Dict:
    """Busca um concurso específico no Supabase"""
    try:
        response = supabase.table("lotofacil_concursos") \
            .select("*") \
            .eq("concurso", numero) \
            .single() \
            .execute()
        return response.data
    except Exception as e:
        print(f"Erro ao buscar concurso {numero}: {e}")
        return None
