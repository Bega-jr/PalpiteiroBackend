from fastapi import APIRouter, HTTPException
from app.services.supabase_service import get_supabase

router = APIRouter(prefix="/concurso", tags=["Concurso"])

@router.get("/ultimo")
def ultimo_concurso():
    """
    Busca os dados completos do último concurso no Supabase.
    """
    try:
        supabase = get_supabase()
        
        # Busca o concurso mais recente ordenando pelo número de forma descendente
        res = (
            supabase.table("lotofacil_concursos")
            .select("*")
            .order("concurso", desc=True)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise HTTPException(status_code=404, detail="Nenhum concurso encontrado no banco de dados.")

        # Retorna o primeiro (e único) item da lista, que é o mais recente (ex: 3582)
        return res.data

    except Exception as e:
        # Registre o erro internamente se necessário
        raise HTTPException(status_code=500, detail=f"Erro interno ao buscar o último concurso: {str(e)}")


@router.get("/{numero}")
def concurso_por_numero(numero: int):
    """
    Busca um concurso específico pelo número no Supabase.
    """
    try:
        supabase = get_supabase()
        res = (
            supabase.table("lotofacil_concursos")
            .select("*")
            .eq("concurso", numero)
            .single()  # Espera exatamente um resultado
            .execute()
        )
        if res.data:
            return res.data
        
        raise HTTPException(status_code=404, detail=f"Concurso {numero} não encontrado.")

    except Exception as e:
        # Trate erros como "nenhum item encontrado" ou "mais de um item encontrado"
        raise HTTPException(status_code=500, detail=f"Erro ao buscar concurso por número: {str(e)}")

