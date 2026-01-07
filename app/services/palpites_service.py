from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import traceback


def obter_todos_palpites_debug():
    try:
        supabase = get_supabase()

        response = (
            supabase
            .table("palpites_validos")
            .select("*")
            .limit(10)
            .execute()
        )

        # LOGS IMPORTANTES (Vercel)
        print("📦 RESPONSE TYPE:", type(response))
        print("📦 RESPONSE DATA:", response.data)

        return response.data or []

    except Exception as e:
        print("🔥 ERRO REAL SUPABASE 🔥")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
