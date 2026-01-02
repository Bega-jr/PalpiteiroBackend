from datetime import date
from app.core.supabase import supabase
from postgrest.exceptions import APIError


def carregar_estatisticas_base():
    hoje = date.today()

    try:
        response = (
            supabase
            .table("estatisticas_numeros")
            .select("numero, frequencia, atraso")
            .eq("data_referencia", hoje)
            .order("numero")
            .execute()
        )

        if response.data:
            return response.data

        # Fallback: último registro disponível
        print(f"INFO: Nenhum dado encontrado para {hoje}. Buscando último registro.")

        fallback = (
            supabase
            .table("estatisticas_numeros")
            .select("numero, frequencia, atraso")
            .order("data_referencia", desc=True)
            .limit(25)  # 25 números da Lotofácil
            .execute()
        )

        return fallback.data or []

    except APIError as e:
        print("ERRO Supabase (base):", e)
        return []
    except Exception as e:
        print("ERRO inesperado (base):", e)
        return []


def carregar_estatisticas_score():
    hoje = date.today()

    try:
        response = (
            supabase
            .table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .eq("data_referencia", hoje)
            .order("score", desc=True)
            .execute()
        )

        if response.data:
            return response.data

        print(f"INFO: Nenhum score encontrado para {hoje}. Buscando último registro.")

        fallback = (
            supabase
            .table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .order("data_referencia", desc=True)
            .limit(25)
            .execute()
        )

        return fallback.data or []

    except APIError as e:
        print("ERRO Supabase (score):", e)
        return []
    except Exception as e:
        print("ERRO inesperado (score):", e)
        return []
