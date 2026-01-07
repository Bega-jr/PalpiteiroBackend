from fastapi import APIRouter
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/home", tags=["Home"])

@router.get("")
def home():
    try:
        resp = (
            supabase
            .from_("vw_lotofacil_stats")
            .select("*")
            .order("concurso", desc=True)
            .limit(1)
            .single()
            .execute()
        )

        data = resp.data

        if not data:
            return {"status": "empty"}

        # 🔹 Normalização defensiva
        data["municipios"] = data.get("municipios") or []
        data["dezenas"] = [int(d) for d in data.get("dezenas", [])]

        return data

    except Exception as e:
        # 🔴 NUNCA deixar estourar exceção na Home
        return {
            "status": "error",
            "message": "Falha ao carregar dados da Home",
            "detail": str(e)
        }
