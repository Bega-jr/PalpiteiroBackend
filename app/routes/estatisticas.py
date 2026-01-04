from fastapi import APIRouter, HTTPException
<<<<<<< HEAD
from datetime import date
=======
>>>>>>> 84934dddddaf9f10699540dd35ddb5ad575dd3f4
from app.core.supabase import supabase

router = APIRouter(prefix="/estatisticas", tags=["Estatísticas"])


@router.get("/")
def get_estatisticas():
    try:
        # 1️⃣ Buscar data mais recente
        data_resp = (
            supabase.table("estatisticas_numeros")
            .select("data_referencia")
            .order("data_referencia", desc=True)
            .limit(1)
            .execute()
        )

<<<<<<< HEAD
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
=======
        if not data_resp.data:
            raise HTTPException(status_code=404, detail="Nenhuma estatística encontrada")

        data_ref = data_resp.data[0]["data_referencia"]

        # 2️⃣ Buscar estatísticas por número
        numeros_resp = (
            supabase.table("estatisticas_numeros")
            .select("numero, frequencia, atraso, score")
            .eq("data_referencia", data_ref)
            .order("score", desc=True)
            .execute()
        )

        numeros = numeros_resp.data or []

        # 3️⃣ Buscar estatísticas diárias (SEM .single())
        diario_resp = (
            supabase.table("estatisticas_diarias_v2")
            .select("*")
            .eq("data_referencia", data_ref)
            .execute()
        )

        if not diario_resp.data:
            raise HTTPException(
                status_code=404,
                detail="Estatísticas diárias não encontradas"
            )

        diario = diario_resp.data[0]

        return {
            "estatisticas": numeros,
            "analise": {
                "soma_media": diario["media_soma"],
                "pares_media": diario["media_pares"],
                "impares_media": diario.get("media_impares"),
                "primos_media": diario.get("media_primos"),
                "data_referencia": hoje
            },
            "ciclo": {
                "faltam": diario.get("numeros_atrasados", []),
                "total_faltam": len(diario.get("numeros_atrasados", []))
            }
        }

    except Exception as e:
        print("❌ ERRO /estatisticas:", e)
        raise HTTPException(status_code=500, detail="Erro interno ao carregar estatísticas")
>>>>>>> 84934dddddaf9f10699540dd35ddb5ad575dd3f4
