from app.services.supabase_service import get_supabase


def obter_pesos_meta_learning():

    supabase = get_supabase()

    rows = (

        supabase
        .table("memoria_meta_learning")
        .select("*")
        .order(
            "updated_at",
            desc=True
        )
        .limit(1)
        .execute()
        .data
    )

    if not rows:

        return {
            "base": 1.0,
            "global": 1.0,
            "feedback": 1.0,
            "regime": 1.0,
            "moldura": 1.0,
            "estrutura": 1.0,
            "fadiga": 1.0,
            "recencia": 1.0
        }

    return rows[0]
