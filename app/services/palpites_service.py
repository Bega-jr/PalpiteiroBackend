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
            .limit(5)
            .execute()
        )

        print("📦 SUPABASE RESPONSE:", response)
        print("📦 SUPABASE DATA:", response.data)
        print("❌ SUPABASE ERROR:", response.error)

        if response.error:
            raise Exception(response.error)

        return response.data or []

    except Exception as e:
        print("🔥 ERRO NO SERVICE DEBUG 🔥")
        print(str(e))
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Erro Supabase: {str(e)}"
        )
