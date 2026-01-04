from fastapi import APIRouter, HTTPException
from datetime import date
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])

@router.get("/")
def get_estatisticas():
    hoje = date.today().isoformat()

    try:
        # 1. Busca estatísticas por número
        response_numeros = (
            supabase.table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .eq("data_referencia", hoje)
            .execute()
        )

        numeros = response_numeros.data or []

        if not numeros:
            # Fallback para o último dia disponível
            fallback = (
                supabase.table("estatisticas_numeros")
                .select("numero, frequencia, atraso, score")
                .order("data_referencia", desc=True)
                .limit(25)
                .execute()
            )
            numeros = fallback.data or []

        # 2. Busca resumo diário
        response_diario = (
            supabase.table("estatisticas_diarias_v2")
            .select("*")
            .eq("data_referencia", hoje)
            .single()
            .execute()
        )

        diario = response_diario.data if response_diario.data else {}

        # Valores padrão caso alguma coluna falte
        return {
            "estatisticas": numeros,
            "analise": {
                "soma_media": round(diario.get("media_soma", 0), 2),
                "pares_media": round(diario.get("media_pares", 7.2), 2),
                "impares_media": round(diario.get("media_impares", 7.8), 2),
                "primos_media": round(diario.get("media_primos", 0), 2),
                "data_referencia": hoje,
            },
            "ciclo": {
                "faltam": diario.get("numeros_atrasados", []) or diario.get("numeros_frios", []),
                "total_faltam": len(diario.get("numeros_atrasados", []) or diario.get("numeros_frios", [])),
            },
        }

    except Exception as e:
        print("Erro no endpoint /estatisticas:", e)
        raise HTTPException(status_code=500, detail="Erro ao carregar estatísticas do banco")