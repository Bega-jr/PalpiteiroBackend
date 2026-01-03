from fastapi import APIRouter
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])


@router.get("/")
def get_estatisticas():
    # 🔹 1. Descobrir a data mais recente disponível
    data_resp = (
        supabase.table("estatisticas_numeros")
        .select("data_referencia")
        .order("data_referencia", desc=True)
        .limit(1)
        .execute()
        .data
    )

    if not data_resp:
        return {"erro": "Nenhuma estatística encontrada"}

    data_ref = data_resp[0]["data_referencia"]

    # 🔹 2. Estatísticas por número
    numeros = (
        supabase.table("estatisticas_numeros")
        .select("numero, frequencia, atraso, score")
        .eq("data_referencia", data_ref)
        .order("score", desc=True)
        .execute()
        .data
    )

    # 🔹 3. Estatísticas diárias
    diario = (
        supabase.table("estatisticas_diarias_v2")
        .select("*")
        .eq("data_referencia", data_ref)
        .single()
        .execute()
        .data
    )

    return {
        "estatisticas": numeros,
        "analise": {
            "soma_media": diario["media_soma"],
            "pares_media": diario["media_pares"],
            "impares_media": diario["media_impares"],
            "primos_media": diario["media_primos"],
            "data_referencia": data_ref
        },
        "ciclo": {
            "faltam": diario["numeros_atrasados"],
            "total_faltam": len(diario["numeros_atrasados"])
        }
    }
