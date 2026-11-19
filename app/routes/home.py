import logging

from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase
import json

router = APIRouter(prefix="/home", tags=["Home"])
logger = logging.getLogger(__name__)


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

    except Exception as exc:
        logger.exception("Falha ao carregar dados da Home")
        raise HTTPException(
            status_code=503,
            detail="Falha ao carregar dados da Home",
        ) from exc
