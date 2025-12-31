from datetime import date
from app.core.supabase import supabase
from supabase.lib.client_options import ClientOptions
from postgrest.base_resource import BaseResource # Importar o necessário para tratamento de exceção, se a lib do Supabase levantar uma.

def carregar_estatisticas_base():
    hoje = date.today()
    
    response = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, frequencia, atraso")
        .eq("data_referencia", hoje)
        .order("numero")
        .execute()
    )
    
    # Se a resposta não tiver dados (lista vazia ou erro 404), tentamos buscar a última data disponível
    if not response.data:
        print(f"INFO: Nenhum dado encontrado para hoje ({hoje}). Buscando o último registro disponível.")
        
        # Fallback: buscar o último registro
        last_data_response = (
            supabase
            .table("estatisticas_numeros")
            .select("numero, frequencia, atraso")
            .order("data_referencia", desc=True)
            .limit(10) # Limite ajustado para pegar os 10 últimos, por exemplo. Ajuste conforme sua necessidade
            .execute()
        )
        return last_data_response.data or [] # Retorna a última data ou uma lista vazia final

    return response.data


def carregar_estatisticas_score():
    hoje = date.today()

    response = (
        supabase
        .table("estatisticas_numeros")
        .select("numero, frequencia, atraso, score")
        .eq("data_referencia", hoje)
        .order("score", desc=True)
        .execute()
    )

    if not response.data:
        print(f"INFO: Nenhum dado de score encontrado para hoje ({hoje}). Buscando o último registro disponível.")

        last_data_response = (
            supabase
            .table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .order("data_referencia", desc=True)
            .limit(10)
            .execute()
        )
        return last_data_response.data or []
        
    return response.data
