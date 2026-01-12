from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase
import json

router = APIRouter(prefix="/home", tags=["Home"])


@router.get("")
def home():
    try:
        supabase = get_supabase()

        resp = (
            supabase
            .table("vw_lotofacil_stats")
            .select("*")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        if not resp.data:
            return {
                "status": "empty",
                "data": None
            }

        data = resp.data[0]

        # 🔹 Normalização defensiva (EXATAMENTE como o front espera)
        data["dezenas"] = [int(d) for d in (data.get("dezenas") or [])]

        if isinstance(data.get("municipios"), str):
            data["municipios"] = json.loads(data["municipios"])
        else:
            data["municipios"] = data.get("municipios") or []

        return {
            "status": "ok",
            "data": data
        }

    except Exception as e:
        return {
            "status": "error",
            "data": None,
            "message": "Falha ao carregar dados da Home",
            "detail": str(e)
        }
