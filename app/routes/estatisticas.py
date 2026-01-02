from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase
from postgrest.exceptions import APIError

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas_dashboard():
    hoje = date.today()

    try:
        # Estatísticas por número (do Supabase)
        response_numeros = supabase.table("estatisticas_numeros") \
            .select("numero, frequencia, atraso, score") \
            .eq("data_referencia", hoje) \
            .execute()

        estatisticas = response_numeros.data or []

        if not estatisticas:
            # Fallback para último registro (evita vazio)
            fallback = supabase.table("estatisticas_numeros") \
                .select("numero, frequencia, atraso, score") \
                .order("data_referencia", desc=True) \
                .limit(25) \
                .execute()
            estatisticas = fallback.data or []

        # Resumo diário
        response_diarias = supabase.table("estatisticas_diarias_v2") \
            .select("*") \
            .eq("data_referencia", hoje) \
            .single() \
            .execute()

        diarias = response_diarias.data if response_diarias.data else {}

        # Monta resposta completa
        return {
            "estatisticas": estatisticas,
            "analise": {
                "soma_media": round(diarias.get("media_soma", 0), 2),
                "pares_media": round(diarias.get("media_pares", 7.2), 1),
                "impares_media": round(15 - diarias.get("media_pares", 7.2), 1),
                "primos_media": 0,  # adicione no script se quiser
                "data_referencia": hoje.isoformat(),
            },
            "ciclo": {
                "faltam": diarias.get("numeros_atrasados", []) or diarias.get("numeros_frios", []),
                "total_faltam": len(diarias.get("numeros_atrasados", []) or diarias.get("numeros_frios", [])),
            }
        }

    except APIError as e:
        print("Erro Supabase:", e)
        raise HTTPException(status_code=500, detail="Erro ao acessar o banco.")
    except Exception as e:
        print("Erro inesperado:", e)
        raise HTTPException(status_code=500, detail="Erro interno.")