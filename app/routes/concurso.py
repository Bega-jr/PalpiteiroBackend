from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def ultimo_concurso():
    """
    Busca o último concurso sorteado no banco de dados.
    """
    try:
        supabase = get_supabase()
        res = (
            supabase.table("lotofacil_concursos")
            .select("*")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail="Nenhum concurso encontrado.")

        # Retorna o primeiro objeto da lista [0]
        return res.data[0]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{numero}")
def concurso_por_numero(numero: int):
    """
    Busca um concurso específico pelo número.
    """
    try:
        supabase = get_supabase()
        res = (
            supabase.table("lotofacil_concursos")
            .select("*")
            .eq("concurso", numero)
            .execute()
        )
        
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=404, detail="Concurso não encontrado.")
            
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

