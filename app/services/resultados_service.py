import os
from typing import List, Dict
from supabase import create_client, Client

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_resultados_supabase(page: int = 1, limit: int = 10) -> Dict:
    """Busca e entrega os dados brutos como texto"""
    try:
        start = (page - 1) * limit
        end = start + limit - 1

        response = supabase.table("lotofacil_concursos") \
            .select("*", count="exact") \
            .order("concurso", descending=True) \
            .range(start, end) \
            .execute()

        # Apenas garante que o campo 'data' seja string e corta o tempo se houver
        for item in response.data:
            if item.get("data"):
                # Se vier "2026-01-08T00:00:00", pega apenas "2026-01-08"
                item["data"] = str(item["data"])[:10]

        return {
            "resultados": response.data,
            "total": response.count
        }
    except Exception as e:
        print(f"Erro Supabase: {e}")
        return {"resultados": [], "total": 0}

def fetch_concurso_unico_supabase(numero: int) -> Dict:
    """Busca um único concurso e mantém a data original"""
    try:
        response = supabase.table("lotofacil_concursos") \
            .select("*") \
            .eq("concurso", numero) \
            .single() \
            .execute()
        
        data = response.data
        if data and data.get("data"):
            data["data"] = str(data["data"])[:10]
            
        return data
    except Exception as e:
        print(f"Erro: {e}")
        return None

