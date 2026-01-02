from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase
from postgrest.exceptions import APIError

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas_dashboard():
    hoje = date.today()

    try:
        # Lê estatísticas por número do Supabase
        response_numeros = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score") \
            .eq("data_referencia", hoje) \
            .execute()

        estatisticas = response_numeros.data

        if not estatisticas:
            raise ValueError("Nenhum dado encontrado para hoje")

        # Lê resumo diário
        response_diarias = supabase.table("estatisticas_diarias_v2") \
            .select("*") \
            .eq("data_referencia", hoje) \
            .single() \
            .execute()

        diarias = response_diarias.data if response_diarias.data else {}

        return {
            "estatisticas": estatisticas,
            "analise": {
                "soma_media": diarias.get("media_soma", 0.0),
                "pares_media": diarias.get("media_pares", 7.2),
                "impares_media": 15 - diarias.get("media_pares", 7.2),
                "primos_media": 0.0,
                "data_referencia": hoje.isoformat(),
            },
            "ciclo": {
                "faltam": diarias.get("numeros_atrasados", []) or diarias.get("numeros_frios", []),
                "total_faltam": len(diarias.get("numeros_atrasados", []) or diarias.get("numeros_frios", [])),
            }
        }

    except Exception as e:
        print("Erro no endpoint /estatisticas:", e)
        raise HTTPException(status_code=500, detail="Erro ao carregar estatísticas do banco.")

# Compatibilidade com chamadas antigas
@router.get("/score")
def get_score():
    hoje = date.today()
    try:
        response = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score") \
            .eq("data_referencia", hoje) \
            .execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/ciclo")
def get_ciclo():
    hoje = date.today()
    try:
        response = supabase.table("estatisticas_diarias_v2") \
            .select("numeros_atrasados, numeros_frios") \
            .eq("data_referencia", hoje) \
            .single() \
            .execute()
        diarias = response.data if response.data else {}
        faltam = diarias.get("numeros_atrasados") or diarias.get("numeros_frios") or []
        return {"faltam": sorted(faltam), "total_faltam": len(faltam)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))