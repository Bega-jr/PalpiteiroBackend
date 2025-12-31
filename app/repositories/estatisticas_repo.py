from datetime import date
from app.core.supabase import supabase

def carregar_estatisticas_base():
    hoje = date.today()
    return (
        supabase
        .table("estatisticas_numeros")
        .select("numero, frequencia, atraso")
        .eq("data_referencia", hoje)
        .order("numero")
        .execute()
        .data
    )

def carregar_estatisticas_score():
    hoje = date.today()
    return (
        supabase
        .table("estatisticas_numeros")
        .select("numero, frequencia, atraso, score")
        .eq("data_referencia", hoje)
        .order("score", desc=True)
        .execute()
        .data
    )
