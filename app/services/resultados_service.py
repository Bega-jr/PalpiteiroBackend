import os
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client

# Configurações do Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def formatar_data_estatica(data_raw: str) -> str:
    """
    Transforma YYYY-MM-DD em DD/MM/YYYY como STRING PURA.
    Isso impede que o navegador do usuário subtraia horas pelo fuso horário.
    """
    if not data_raw:
        return ""
    try:
        # Pega apenas a parte da data (YYYY-MM-DD)
        data_str = str(data_raw)[:10].replace("/", "-")
        # Converte para objeto e gera string brasileira
        dt = datetime.strptime(data_str, "%Y-%m-%d")
        return dt.strftime("%d/%m/%Y")
    except Exception:
        # Se der erro ou já for BR, retorna como está
        return str(data_raw)

def fetch_resultados_supabase(page: int = 1, limit: int = 10) -> Dict:
    """Busca resultados e já formata a data no servidor"""
    try:
        start = (page - 1) * limit
        end = start + limit - 1

        response = supabase.table("lotofacil_concursos") \
            .select("*", count="exact") \
            .order("concurso", descending=True) \
            .range(start, end) \
            .execute()

        # Normaliza a data de cada concurso antes de enviar
        for item in response.data:
            item["data"] = formatar_data_estatica(item.get("data"))

        return {
            "resultados": response.data,
            "total": response.count
        }
    except Exception as e:
        print(f"Erro Supabase: {e}")
        return {"resultados": [], "total": 0}

def fetch_concurso_unico_supabase(numero: int) -> Dict:
    """Busca um concurso único e formata a data"""
    try:
        response = supabase.table("lotofacil_concursos") \
            .select("*") \
            .eq("concurso", numero) \
            .single() \
            .execute()
        
        data = response.data
        if data:
            data["data"] = formatar_data_estatica(data.get("data"))
            
        return data
    except Exception as e:
        print(f"Erro ao buscar concurso {numero}: {e}")
        return None

