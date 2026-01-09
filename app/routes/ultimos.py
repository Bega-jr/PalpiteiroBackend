from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/ultimos", tags=["Últimos"])

@router.get("/{quantidade}")
def listar_ultimos(quantidade: int):
    """
    Lista os 'quantidade' últimos concursos do Supabase.
    """
    if quantidade <= 0:
        raise HTTPException(status_code=400, detail="A quantidade deve ser um número positivo.")

    try:
        supabase = get_supabase()
        historico = (
            supabase.table("lotofacil_concursos")
            .select("*")
            .order("concurso", desc=True)
            .limit(quantidade)
            .execute()
        )

        if not historico.data:
            return [] # Retorna uma lista vazia se não houver dados

        # Se a quantidade for 1, retorna o objeto diretamente, senão retorna a lista
        if quantidade == 1:
            return historico.data[0]
        
        return historico.data

    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Erro ao listar últimos concursos: {str(e)}")

