import os
from datetime import datetime
from typing import List, Dict
from supabase import create_client, Client

# Configurações do Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def formatar_data_para_br(data_raw: str) -> str:
    """
    Converte '2026-01-08' ou '2003-09-29T00:00:00' para '08/01/2026' ou '29/09/2003'.
    Isso evita que o Frontend JavaScript erre o fuso horário.
    """
    if not data_raw:
        return ""
    try:
        # Pega apenas os primeiros 10 caracteres (ignora T00:00:00 se houver)
        data_limpa = str(data_raw)[:10]
        
        # Converte YYYY-MM-DD para objeto date e depois para DD/MM/YYYY
        data_obj = datetime.strptime(data_limpa, "%Y-%m-%d")
        return data_obj.strftime("%d/%m/%Y")
    except Exception:
        # Se a data já estiver formatada ou for inválida, retorna o original
        return str(data_raw)

def fetch_resultados_supabase(page: int = 1, limit: int = 10) -> Dict:
    """Busca resultados paginados do Supabase com data formatada"""
    try:
        start = (page - 1) * limit
        end = start + limit - 1

        response = supabase.table("lotofacil_concursos") \
            .select("*", count="exact") \
            .order("concurso", descending=True) \
            .range(start, end) \
            .execute()

        # FORMATAÇÃO: Tratamos a data de cada item antes de enviar para o Frontend
        resultados_formatados = []
        for item in response.data:
            item["data"] = formatar_data_para_br(item.get("data"))
            resultados_formatados.append(item)

        return {
            "resultados": resultados_formatados,
            "total": response.count
        }
    except Exception as e:
        print(f"Erro Supabase: {e}")
        return {"resultados": [], "total": 0}

def fetch_concurso_unico_supabase(numero: int) -> Dict:
    """Busca um concurso específico no Supabase com data formatada"""
    try:
        response = supabase.table("lotofacil_concursos") \
            .select("*") \
            .eq("concurso", numero) \
            .single() \
            .execute()
        
        data = response.data
        if data:
            data["data"] = formatar_data_para_br(data.get("data"))
            
        return data
    except Exception as e:
        print(f"Erro ao buscar concurso {numero}: {e}")
        return None
