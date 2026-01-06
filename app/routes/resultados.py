from fastapi import APIRouter, HTTPException, Query
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/resultados", tags=["Resultados"])


@router.get("/total")
def total_concursos():
    """
    Retorna o total de concursos cadastrados
    """
    try:
        supabase = get_supabase()

        resp = supabase.table("lotofacil_concursos") \
            .select("concurso", count="exact") \
            .execute()

        return {
            "status": "ok",
            "total": resp.count
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("")
def listar_resultados(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Lista concursos paginados (do mais recente para o mais antigo)
    """
    try:
        supabase = get_supabase()

        start = (page - 1) * limit
        end = start + limit - 1

        resp = supabase.table("lotofacil_concursos") \
            .select("*") \
            .order("concurso", desc=True) \
            .range(start, end) \
            .execute()

        return {
            "status": "ok",
            "page": page,
            "limit": limit,
            "resultados": resp.data
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{concurso}")
def obter_concurso(concurso: int):
    """
    Retorna um concurso específico
    """
    try:
        supabase = get_supabase()

        resp = supabase.table("lotofacil_concursos") \
            .select("*") \
            .eq("concurso", concurso) \
            .single() \
            .execute()

        if not resp.data:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {concurso} não encontrado"
            )

        return {
            "status": "ok",
            "concurso": resp.data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
