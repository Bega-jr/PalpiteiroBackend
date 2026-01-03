from fastapi import APIRouter, HTTPException
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
