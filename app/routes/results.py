from fastapi import APIRouter, HTTPException, Query
from app.services.supabase_client import supabase

router = APIRouter(prefix="/resultados", tags=["Resultados"])


# ================================
# TOTAL DE CONCURSOS
# ================================
@router.get("/total")
def total_concursos():
    try:
        resp = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso", count="exact")
            .execute()
        )

        return {"total": resp.count or 0}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# LISTA PAGINADA (mais recentes)
# ================================
@router.get("")
def listar_resultados(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
):
    try:
        offset = (page - 1) * limit
        to = offset + limit - 1

        resp = (
            supabase
            .table("lotofacil_concursos")
            .select(
                "concurso, data, dezenas, acumulado",
            )
            .order("concurso", desc=True)
            .range(offset, to)
            .execute()
        )

        return {
            "page": page,
            "limit": limit,
            "resultados": resp.data or [],
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ================================
# CONCURSO ESPECÍFICO
# ================================
@router.get("/concurso/{numero}")
def obter_concurso(numero: int):
    try:
        resp = (
            supabase
            .table("lotofacil_concursos")
            .select("*")
            .eq("concurso", numero)
            .single()
            .execute()
        )

        if not resp.data:
            raise HTTPException(
                status_code=404,
                detail=f"Concurso {numero} não encontrado"
            )

        return {"concurso": resp.data}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
