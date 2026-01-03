from fastapi import APIRouter
from datetime import date
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas():
    hoje = date.today().isoformat()

    numeros = supabase.table("estatisticas_numeros") \
        .select("numero, frequencia, atraso, score") \
        .eq("data_referencia", hoje) \
        .execute().data

    diario = supabase.table("estatisticas_diarias_v2") \
        .select("*") \
        .eq("data_referencia", hoje) \
        .single() \
        .execute().data

    return {
        "estatisticas": numeros,
        "analise": {
            "soma_media": diario["media_soma"],
            "pares_media": diario["media_pares"],
            "impares_media": diario["media_impares"],
            "primos_media": diario["media_primos"],
            "data_referencia": hoje
        },
        "ciclo": {
            "faltam": diario["numeros_atrasados"],
            "total_faltam": len(diario["numeros_atrasados"])
        }
    }
