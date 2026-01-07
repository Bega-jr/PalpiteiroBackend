from app.services.supabase_service import get_supabase
from fastapi import HTTPException
import traceback


def _buscar_palpites_por_data():
    """
    Busca TODOS os palpites da data mais recente
    """
    try:
        supabase = get_supabase()

        response = (
            supabase
            .table("palpites_validos")
            .select("*")
            .order("data_referencia", desc=True)
            .order("indice_palpite")
            .execute()
        )

        return response.data or []

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


def obter_palpite_fixo_publico():
    dados = _buscar_palpites_por_data()

    for r in dados:
        if r.get("indice_palpite") == 0:
            return r

    return None


def obter_palpites_estatisticos_publico():
    dados = _buscar_palpites_por_data()

    return [
        r for r in dados
        if r.get("indice_palpite", 0) > 0
    ]
