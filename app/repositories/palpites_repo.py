from app.core.supabase import supabase
from datetime import date

def listar_palpites_hoje():
    hoje = date.today().isoformat()
    return (
        supabase
        .table("palpites_validos")
        .select("*")
        .eq("data_referencia", hoje)
        .order("indice_palpite")
        .execute()
        .data
    )

def carregar_palpite_fixo():
    hoje = date.today().isoformat()
    return (
        supabase
        .table("palpites_validos")
        .select("numeros")
        .eq("data_referencia", hoje)
        .eq("indice_palpite", 1)
        .single()
        .execute()
        .data["numeros"]
    )
