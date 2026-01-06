from fastapi import APIRouter, HTTPException, Query
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/resultados", tags=["Resultados"])

supabase = get_supabase()


@router.get("")
def listar_resultados(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50)
):
    """
    Lista concursos da Lotofácil com paginação
    Ordenado do mais recente para o mais antigo
    """
    try:
        offset = (page - 1) * limit

        resp = (
            supabase
            .table("lotofacil_concursos")
            .select(
                "concurso, data, dezenas, soma, pares, impares"
            )
            .order("concurso", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        return {
            "status": "ok",
            "page": page,
            "limit": limit,
            "resultados": resp.data or []
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/total")
def total_resultados():
    """
    Retorna total de concursos cadastrados
    """
    try:
        resp = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso", count="exact")
            .execute()
        )

        return {
            "status": "ok",
            "total": resp.count or 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{numero}")
def obter_concurso(numero: int):
    """
    Retorna um concurso específico
    """
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

        return {
            "status": "ok",
            "concurso": resp.data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
