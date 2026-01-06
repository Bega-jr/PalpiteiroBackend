from fastapi import APIRouter, HTTPException, Query
from app.core.supabase import supabase

router = APIRouter(
    prefix="/resultados",
    tags=["Resultados"]
)

# ======================================================
# 🔹 Concurso individual
# ======================================================
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

        return {
            "status": "ok",
            "concurso": resp.data
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ======================================================
# 🔹 Lista paginada (do último para o primeiro)
# ======================================================
@router.get("")
def listar_resultados(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50)
):
    """
    Lista concursos da Lotofácil
    Ordenados do mais recente para o mais antigo
    """

    try:
        inicio = (page - 1) * limit
        fim = inicio + limit - 1

        resp = (
            supabase
            .table("lotofacil_concursos")
            .select(
                """
                concurso,
                data,
                dezenas,
                soma,
                pares,
                impares,
                acumulado
                """
            )
            .order("concurso", desc=True)
            .range(inicio, fim)
            .execute()
        )

        return {
            "status": "ok",
            "page": page,
            "limit": limit,
            "quantidade": len(resp.data),
            "resultados": resp.data
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ======================================================
# 🔹 Total de concursos (para paginação no frontend)
# ======================================================
@router.get("/total")
def total_concursos():
    try:
        resp = (
            supabase
            .table("lotofacil_concursos")
            .select("concurso", count="exact")
            .execute()
        )

        return {
            "status": "ok",
            "total": resp.count
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
