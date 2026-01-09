from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def ultimo_concurso():
    """
    Retorna o objeto do último concurso sorteado (Ex: 3582).
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

        # Retorna o objeto direto (index 0) para o Frontend não receber uma lista
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
        
        if not res.data:
            raise HTTPException(status_code=404, detail="Concurso não encontrado.")
            
        return res.data[0]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

